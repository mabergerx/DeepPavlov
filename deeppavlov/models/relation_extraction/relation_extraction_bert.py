from logging import getLogger
from typing import List, Optional, Dict, Tuple, Union

import numpy as np
import torch
from torch import nn, Tensor

from deeppavlov.core.common.errors import ConfigError
from deeppavlov.core.common.registry import register
from deeppavlov.core.models.torch_model import TorchModel
from deeppavlov.models.classifiers.re_bert import BertWithAdaThresholdLocContextPooling

log = getLogger(__name__)


@register('re_classifier')
class REBertModel(TorchModel):

    def __init__(
            self,
            n_classes: int,
            num_ner_tags: int,
            pretrained_bert: str = None,
            criterion: str = "CrossEntropyLoss",
            return_probas: bool = False,
            attention_probs_keep_prob: Optional[float] = None,
            hidden_keep_prob: Optional[float] = None,
            clip_norm: Optional[float] = None,
            threshold: Optional[float] = None,
            device: str = "cpu",
            **kwargs
    ) -> None:
        """
        Transformer-based model on PyTorch for relation extraction. It predicts a relation hold between entities in a
        text sample (one or several sentences).
        Args:
            n_classes: number of output classes
            num_ner_tags: number of NER tags
            pretrained_bert: key title of pretrained Bert model (e.g. "bert-base-uncased")
            criterion: criterion name from `torch.nn`
            return_probas: set this to `True` if you need the probabilities instead of raw answers
            attention_probs_keep_prob: keep_prob for Bert self-attention layers
            hidden_keep_prob: keep_prob for Bert hidden layers
            clip_norm: clip gradients by norm
            threshold: manually set value for defining the positively predicted classes (instead of adaptive one)
            device: cpu/gpu device to use for training the model
        """
        self.n_classes = n_classes
        self.return_probas = return_probas
        self.attention_probs_keep_prob = attention_probs_keep_prob
        self.hidden_keep_prob = hidden_keep_prob
        self.clip_norm = clip_norm
        self.device = device

        if self.n_classes == 0:
            raise ConfigError("Please provide a valid number of classes.")

        self.model = BertWithAdaThresholdLocContextPooling(
            n_classes=self.n_classes,
            pretrained_bert=pretrained_bert,
            bert_tokenizer_config_file=pretrained_bert,
            num_ner_tags=num_ner_tags,
            threshold=threshold,
            device=self.device
        )

        super().__init__(criterion=criterion, **kwargs)

    def train_on_batch(
            self, input_ids: List, attention_mask: List, entity_pos: List, entity_tags: List, labels: List
    ) -> float:
        """
        Trains the relation extraction BERT model on the given batch.
        Returns:
            dict with loss and learning rate values.
        """

        _input = {
            'input_ids': torch.LongTensor(input_ids).to(self.device),
            'attention_mask': torch.LongTensor(attention_mask).to(self.device),
            'entity_pos': entity_pos,
            'ner_tags': entity_tags,
            'labels': labels
        }

        self.model.train()
        self.model.zero_grad()
        self.optimizer.zero_grad()      # zero the parameter gradients

        hidden_states = self.model(**_input)
        loss = hidden_states[0]
        loss.backward()
        self.optimizer.step()

        # Clip the norm of the gradients to prevent the "exploding gradients" problem
        if self.clip_norm:
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.clip_norm)

        return loss.item()

    def __call__(
            self, input_ids: List, attention_mask: List, entity_pos: List, entity_tags: List
    ) -> Union[List[int], List[np.ndarray]]:
        """ Get model predictions using features as input """

        self.model.eval()

        _input = {
            'input_ids': torch.LongTensor(input_ids).to(self.device),
            'attention_mask': torch.LongTensor(attention_mask).to(self.device),
            'entity_pos': entity_pos,
            'ner_tags': entity_tags
        }

        with torch.no_grad():
            indices, probas = self.model(**_input)

        if self.return_probas:
            pred = probas.cpu().numpy()
            pred[np.isnan(pred)] = 0
            pred_without_no_rel = []        # eliminate no_relation predictions
            for elem in pred:
                elem[0] = 0.0
                pred_without_no_rel.append(elem)
            new_pred = np.argmax(pred_without_no_rel, axis=1)
            one_hot = [[0.0] * self.n_classes] * len(new_pred)
            for i in range(len(new_pred)):
                one_hot[i][new_pred[i]] = 1.0
            pred = np.array(one_hot)
        else:
            pred = indices.cpu().numpy()
            pred[np.isnan(pred)] = 0
        return pred
