from typing import Optional, Set, Tuple
import logging

from overrides import overrides
from conllu.parser import parse_line, DEFAULT_FIELDS

from allennlp.common.file_utils import cached_path
from allennlp.data.dataset_readers.dataset_reader import DatasetReader

from contexteval.data.dataset_readers import TaggingDatasetReader

logger = logging.getLogger(__name__)


def lazy_parse(text: str, fields: Tuple = DEFAULT_FIELDS):
    for sentence in text.split("\n\n"):
        if sentence:
            yield [parse_line(line, fields)
                   for line in sentence.split("\n")
                   if line and not line.strip().startswith("#")]


@DatasetReader.register("conllu_pos")
class ConllUPOSDatasetReader(TaggingDatasetReader):
    """
    Reads a file in the conllu Universal Dependencies format and returns
    instances suitable for POS tagging.

    Parameters
    ----------
    contextualizer: Contextualizer, optional (default=``None``)
        If provided, it is used to produce contextualized representations of the text.
    max_instances: int or float, optional (default=``None``)
        The number of instances to use during training. If int, this value is taken
        to be the absolute amount of instances to use. If float, this value indicates
        that we should use that proportion of the total training data. If ``None``,
        all instances are used.
    seed: int, optional (default=``0``)
        The random seed to use.
    lazy : ``bool``, optional (default=``False``)
        If this is true, ``instances()`` will return an object whose ``__iter__`` method
        reloads the dataset each time it's called. Otherwise, ``instances()`` returns a list.
    """

    @overrides
    def _read_dataset(self,
                      file_path: str,
                      count_only: bool = False,
                      keep_idx: Optional[Set[int]] = None):
        """
        Yield instances from the file_path.

        Parameters
        ----------
        file_path: str, required
            The path to the data file.
        count_only: bool, optional (default=``False``)
            If True, no instances are returned and instead a dummy object is
            returned. This is useful for quickly counting the number of instances
            in the data file, since creating instances is relatively expensive.
        keep_idx: Set[int], optional (default=``None``)
            If not None, only yield instances whose index is in this set.
        """
        file_path = cached_path(file_path)

        if count_only:
            logger.info("Counting POS tagging instances in CoNLL-U formatted dataset at: %s", file_path)
        else:
            logger.info("Reading POS tagging data from CoNLL-U formatted dataset at: %s", file_path)

        with open(file_path, 'r') as tagging_file:
            for i, annotation in enumerate(lazy_parse(tagging_file.read())):
                if count_only:
                    yield 1
                    continue
                if keep_idx is not None and i not in keep_idx:
                    continue
                tokens = [x["form"] for x in annotation]
                # Contextualize the tokens if a Contextualizer was provided.
                # TODO (nfliu): How can we make this batched?
                # Would make contextualizers that use the GPU much faster.
                if self._contextualizer:
                    token_representations = self._contextualizer([tokens])[0]
                else:
                    token_representations = None

                yield self.text_to_instance(
                    tokens,
                    token_representations,
                    [x["upostag"] for x in annotation])
