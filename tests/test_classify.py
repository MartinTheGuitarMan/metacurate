from metacurate.catalog import CatalogItem
from metacurate.classify import classify
from metacurate.models import NoulAnswer


class FakeSystemOneClient:
    def __init__(self, probabilities):
        self.probabilities = probabilities
        self.last_state = None
        self.last_questions = None

    def ask_noul(self, state, questions):
        self.last_state = state
        self.last_questions = questions
        return [NoulAnswer(id=q.id, probability=self.probabilities[q.id]) for q in questions]


def test_classify_ranks_labels_by_probability_descending():
    labels = [
        CatalogItem(id="spam", metadata={"description": "unsolicited bulk email"}),
        CatalogItem(id="not_spam", metadata={"description": "a legitimate message"}),
    ]
    client = FakeSystemOneClient({"spam": 0.9, "not_spam": 0.1})

    ranked = classify(client, "Buy now, limited offer!!!", labels)

    assert ranked == [("spam", 0.9), ("not_spam", 0.1)]


def test_classify_evaluates_every_label_against_the_shared_state():
    labels = [CatalogItem(id="a", metadata={"description": "desc a"})]
    client = FakeSystemOneClient({"a": 0.5})

    classify(client, "raw sample", labels)

    assert client.last_state == "raw sample"
    assert len(client.last_questions) == 1
    assert "desc a" in client.last_questions[0].statement
