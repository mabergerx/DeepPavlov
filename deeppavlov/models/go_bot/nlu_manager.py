from typing import Any, Tuple, List

from deeppavlov import Chainer


# todo logging
class NLUManager:
    """
    NLUManager is a unit of the go-bot pipeline that handles the understanding of text.
    Given the text it provides tokenization, intents extraction and the slots extraction.
    (the whole go-bot pipeline is as follows: NLU, dialogue-state-tracking&policy-NN, NLG)
    """

    def __init__(self, tokenizer, slot_filler, intent_classifier):
        # todo type hints
        self.tokenizer = tokenizer
        self.slot_filler = slot_filler
        self.intent_classifier = intent_classifier
        self.intents = []
        if isinstance(self.intent_classifier, Chainer):
            self.intents = self.intent_classifier.get_main_component().classes

    def nlu(self, text: str) -> Tuple[Any, Any, Any]:
        # todo meaningful type hints
        tokens = self.tokenize_single_text_entry(text)

        slots = None
        if callable(self.slot_filler):
            slots = self.extract_slots_from_tokenized_text_entry(tokens)

        intents = []
        if callable(self.intent_classifier):
            intents = self.extract_intents_from_tokenized_text_entry(tokens)

        return slots, intents, tokens

    def extract_intents_from_tokenized_text_entry(self, tokens: List[str]):
        # todo meaningful type hints, relies on unannotated intent classifier
        intent_features = self.intent_classifier([' '.join(tokens)])[1][0]
        return intent_features

    def extract_slots_from_tokenized_text_entry(self, tokens: List[str]):
        # todo meaningful type hints, relies on unannotated slot filler
        return self.slot_filler([tokens])[0]

    def tokenize_single_text_entry(self, text: str):
        # todo meaningful type hints, relies on unannotated tokenizer
        return self.tokenizer([text.lower().strip()])[0]

    def num_of_known_intents(self) -> int:
        """:returns: the number of intents known to the NLU module"""
        return len(self.intents)