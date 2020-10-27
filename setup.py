from setuptools import setup, find_packages

extras_requires = {
    "spacy": ["spacy>=2.1,<2.2"],
}

setup(
    name='bothub_nlp_rasa_utils',
    version='1.1.27dev',
    description='Bothub NLP Rasa Utils',
    packages=find_packages(),
    package_data={'bothub_nlp_rasa_utils.lookup_tables': ['en/location.txt', 'pt_br/flavor.txt', 'pt_br/location.txt']},
    install_requires=[
        'rasa==1.10.6',
        'transformers==2.11.0',
        'emoji==0.6.0',
        'recognizers-text-suite'
    ],
    extras_require=extras_requires,
)
