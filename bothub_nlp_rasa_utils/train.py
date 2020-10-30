from tempfile import mkdtemp
import os

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


def load_lookup_tables(update_request):
    lookup_tables = []
    language = update_request.get("language")

    # Try to load lookup_tables
    if update_request.get("use_lookup_tables"):
        # Check if lookup_table exists
        # TODO: load lookup tables from backend instead of this (locally)
        runtime_path = os.path.dirname(os.path.abspath(__file__))
        for lookup_table in update_request.get("use_lookup_tables"):
            file_path = f'{runtime_path}/lookup_tables/{language}/{lookup_table}.txt'
            if os.path.exists(file_path):
                lookup_tables.append(
                    {'name': lookup_table, 'elements': file_path},
                )
            else:
                print("Not found lookup_table in path: " + file_path)

    return lookup_tables


def train_update(repository_version, by, repository_authorization, from_queue='celery'):  # pragma: no cover
    update_request = backend().request_backend_start_training_nlu(
        repository_version, by, repository_authorization, from_queue
    )

    """ update_request (v2/repository/nlp/authorization/train/start_training/) signature:
    {
        'language': 'pt_br', 
        'repository_version': 47, 
        'repository_uuid': '1d8e0d6f-1941-42a3-84c5-788706c7072e', 
        'intent': [4, 5], 
        'algorithm': 'transformer_network_diet_bert', 
        'use_name_entities': False, 
        'use_competing_intents': False, 
        'use_analyze_char': False, 
        'total_training_end': 0
    }
    """
    # TODO: update_request must include list of
    #       lookup_tables the user choose to use in webapp
    #       Example:
    update_request["use_lookup_tables"] = ['country', 'cep', 'cpf', 'brand']

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

            lookup_tables = load_lookup_tables(update_request)
            print("Loaded lookup_tables: " + str(lookup_tables))

            rasa_nlu_config = get_rasa_nlu_config(update_request)
            trainer = Trainer(rasa_nlu_config, ComponentBuilder(use_cache=False))
            training_data = TrainingData(
                training_examples=examples,
                lookup_tables=lookup_tables,
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
