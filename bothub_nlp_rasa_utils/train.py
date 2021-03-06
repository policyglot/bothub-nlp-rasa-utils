from tempfile import mkdtemp

from rasa.nlu import __version__ as rasa_version
from rasa.nlu.model import Trainer
from rasa.nlu.training_data import Message, TrainingData
from rasa.nlu.components import ComponentBuilder

from .utils import PokeLogging
from .utils import backend
from .utils import get_examples_request
from .persistor import BothubPersistor
from bothub_nlp_rasa_utils import logger
from .pipeline_builder import get_rasa_nlu_config


def train_update(repository_version, by, repository_authorization, from_queue='celery'):  # pragma: no cover
    update_request = backend().request_backend_start_training_nlu(
        repository_version, by, repository_authorization, from_queue
    )

    examples_list = get_examples_request(repository_version, repository_authorization)

    with PokeLogging() as pl:
        try:
            examples = []

            for example in examples_list:
                examples.append(
                    Message.build(
                        text=example.get("text"),
                        intent=example.get("intent"),
                        entities=example.get("entities"),
                    )
                )

            rasa_nlu_config = get_rasa_nlu_config(update_request)
            trainer = Trainer(rasa_nlu_config, ComponentBuilder(use_cache=False))
            training_data = TrainingData(
                training_examples=examples
            )

            trainer.train(training_data)

            persistor = BothubPersistor(
                repository_version, repository_authorization, rasa_version
            )
            trainer.persist(
                mkdtemp(),
                persistor=persistor,
                fixed_model_name=f"{update_request.get('repository_version')}_"
                f"{update_request.get('total_training_end')+1}_"
                f"{update_request.get('language')}",
            )
        except Exception as e:
            logger.exception(e)
            backend().request_backend_trainfail_nlu(
                repository_version, repository_authorization
            )
            raise e
        finally:
            backend().request_backend_traininglog_nlu(
                repository_version, pl.getvalue(), repository_authorization
            )
