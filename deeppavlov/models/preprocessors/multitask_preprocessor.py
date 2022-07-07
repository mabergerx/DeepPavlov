from typing import Iterable, Union, List,Tuple
from logging import getLogger

from deeppavlov.core.common.registry import register
from deeppavlov.core.models.component import Component
from deeppavlov.models.preprocessors.torch_transformers_preprocessor import *

log = getLogger(__name__)





from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from deeppavlov.core.common.registry import register
from logging import getLogger

log = getLogger(__name__)



@register("multitask_input_splitter")
class MultiTaskInputSplitter:
    """The instance of these class in pipe splits a batch of sequences of identical length or dictionaries with 
    identical keys into tuple of batches.

    Args:
        keys_to_extract: a sequence of ints or strings that have to match keys of split dictionaries.
    """

    def __init__(self, keys_to_extract: Union[List[str], Tuple[str, ...]], **kwargs):
        self.keys_to_extract = keys_to_extract

    def __call__(self, inp: Union[List[dict], List[List[int]], List[Tuple[int]]]) -> Union[List[list], List[str]]:
        """Returns batches of values from ``inp``. Every batch contains values that have same key from 
        ``keys_to_extract`` attribute. The order of elements of ``keys_to_extract`` is preserved.

        Args:
            inp: A sequence of dictionaries with identical keys

        Returns:
            A list of lists of values of dictionaries from ``inp``
        """
        if all([isinstance(k, str) for k in inp]):
            log.warning('You want to split an input that is already string')
            return inp

        extracted = [[] for _ in self.keys_to_extract]
        for item in inp:
            for i, key in enumerate(self.keys_to_extract):
                if key < len(item):
                    extracted[i].append(item[key])
        print('got')
        print(extracted)
        return extracted

@register('multitask_pipeline_preprocessor')
class MultiTaskPipelinePreprocessor(Component):
    """
    Extracts out the task_id from the first index of each example for each task.
    Then splits the input and performs tokenization
    """

    def __init__(self, possible_keys_to_extract,
                 vocab_file,
                 do_lower_case: bool = True,
                 preprocessor: str='TorchTransformersPreprocessor',
                 preprocessors=None, 
                 max_seq_length: int = 512, 
                 return_tokens: bool = False, 
                 n_task: int = 3,
                 *args, **kwargs):
        self.n_task = n_task
        if isinstance(possible_keys_to_extract, str):
            log.info(f'Assuming {possible_keys_to_extract} can be casted to list or list of lists')
            possible_keys_to_extract = eval(possible_keys_to_extract)
        if not isinstance(possible_keys_to_extract[0], list):
            self.input_splitters = [MultiTaskInputSplitter(keys_to_extract=possible_keys_to_extract)]
        if isinstance(possible_keys_to_extract[0],list):
            log.info(f'Utilizing many input splitters with sets {possible_keys_to_extract} Number of sets must be the same as task number')
            assert len(possible_keys_to_extract) == self.n_task
            self.input_splitters = [MultiTaskInputSplitter(keys_to_extract=keys) for keys in possible_keys_to_extract]
        else:
            self.input_splitters = [MultiTaskInputSplitter(keys_to_extract=possible_keys_to_extract)
                                    for _ in range(self.n_task)]
        if preprocessors is None:
            log.info(f'Assuming the same preprocessor name for all : {preprocessor}')
            assert preprocessor is not None
            preprocessor = eval(preprocessor)
            self.preprocessors=[preprocessor(vocab_file, do_lower_case, max_seq_length)
                                for _ in range(self.n_task)]
        else:
            assert len(preprocessors) == self.n_task
            for i in range(len(preprocessors)):
                preprocessors[i] = eval(preprocessors[i]) 
            self.preprocessors = [preprocessors[i](vocab_file, do_lower_case, max_seq_length)
                                  for i in range(self.n_task)]


    def __call__(self, *args):
        """Returns batches of values from ``inp``. Every batch contains values that have same key from 
        ``keys_to_extract`` attribute. The order of elements of ``keys_to_extract`` is preserved.

        Args:
            inp: A sequence of dictionaries with identical keys

        Returns:
            A list of lists of values of dictionaries from ``inp``
        """
        #print('calling pipeline')
        #print(args)
        assert len(args) == self.n_task, "Seen examples from {len(args)} tasks but n_task specified to {self.n_task}"
        print(f'Receiving in preprocessor {args}')
        answer = []
        for i in range(len(args)):
            print(f'Before splitting {args[i]}')
            if all([j== None for j in args[i]]):
                print('All nones received')
                answer.append([])
            else:
                if all([isinstance(k,str) for k in args[i]]):
                    print('All strings  - not splitting')
                    texts_a, texts_b = args[i], None
                else:
                    texts_a, texts_b = self.input_splitters[i](args[i])
                    print(f'After splitting {texts_a} AND {texts_b}')
                assert texts_a is not None
                print(f'Preprocessor {self.preprocessors[i]}')
                if i == 4:
                    print('CHECK THOROUGHLY THE NER OUTPUT')
                    breakpoint()
                answer.append(self.preprocessors[i](texts_a, texts_b))
        return answer
