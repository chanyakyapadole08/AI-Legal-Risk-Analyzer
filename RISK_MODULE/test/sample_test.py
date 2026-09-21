import spacy
from transformers import pipeline

print("Loading SpaCy...")

nlp = spacy.load("en_core_web_sm")

print("SpaCy OK")

print("Loading Legal BERT...")

classifier = pipeline(
    "text-classification",
    model="nlpaueb/legal-bert-base-uncased"
)

print("Transformers OK")
print("Everything Ready")