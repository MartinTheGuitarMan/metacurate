from metacurate.catalog import CatalogItem
from metacurate.models import JevModel, NoulAnswer, NoulQuestion


class FakeJevClient:
    def __init__(self, probabilities):
        self.probabilities = probabilities
        self.last_state = None
        self.last_questions = None

    def ask_noul(self, state, questions):
        self.last_state = state
        self.last_questions = questions
        return [NoulAnswer(id=q.id, probability=self.probabilities[q.id]) for q in questions]


def test_jev_model_ranks_by_probability_descending():
    items = [
        CatalogItem(id="a", metadata={"name": "Alpha"}),
        CatalogItem(id="b", metadata={"name": "Beta"}),
        CatalogItem(id="c", metadata={"name": "Gamma"}),
    ]
    model = JevModel(client=FakeJevClient({"a": 0.2, "b": 0.9, "c": 0.5}))

    picks = model.curate(items, "demo use case", limit=2)

    assert [item_id for item_id, _ in picks] == ["b", "c"]
    assert "0.90" in picks[0][1]


def test_jev_model_asks_one_noul_question_per_item():
    items = [CatalogItem(id="a", metadata={}), CatalogItem(id="b", metadata={})]
    client = FakeJevClient({"a": 0.1, "b": 0.1})
    model = JevModel(client=client)

    model.curate(items, "demo", limit=2)

    assert len(client.last_questions) == 2
    assert all(isinstance(q, NoulQuestion) for q in client.last_questions)
    assert all("demo" in q.statement for q in client.last_questions)
