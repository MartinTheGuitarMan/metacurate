from metacurate.catalog import CatalogItem
from metacurate.models import (
    ChoiceAnswer,
    ChoiceQuestion,
    NoulAnswer,
    NoulQuestion,
    SystemOneClassifier,
    SystemOneModel,
)


class FakeSystemOneClient:
    def __init__(self, probabilities):
        self.probabilities = probabilities
        self.last_state = None
        self.last_questions = None

    def ask_noul(self, state, questions):
        self.last_state = state
        self.last_questions = questions
        return [NoulAnswer(id=q.id, probability=self.probabilities[q.id]) for q in questions]


def test_system_one_model_ranks_by_probability_descending():
    items = [
        CatalogItem(id="a", metadata={"name": "Alpha"}),
        CatalogItem(id="b", metadata={"name": "Beta"}),
        CatalogItem(id="c", metadata={"name": "Gamma"}),
    ]
    model = SystemOneModel(client=FakeSystemOneClient({"a": 0.2, "b": 0.9, "c": 0.5}))

    picks = model.curate(items, "demo use case", limit=2)

    assert [item_id for item_id, _ in picks] == ["b", "c"]
    assert "0.90" in picks[0][1]


def test_system_one_model_asks_one_noul_question_per_item():
    items = [CatalogItem(id="a", metadata={}), CatalogItem(id="b", metadata={})]
    client = FakeSystemOneClient({"a": 0.1, "b": 0.1})
    model = SystemOneModel(client=client)

    model.curate(items, "demo", limit=2)

    assert len(client.last_questions) == 2
    assert all(isinstance(q, NoulQuestion) for q in client.last_questions)
    assert all("demo" in q.statement for q in client.last_questions)


class FakeChoiceClient:
    def __init__(self, choices):
        self.choices = choices  # {item_id: (choice, confidence)}
        self.last_state = None
        self.last_questions = None

    def ask_choice(self, state, questions):
        self.last_state = state
        self.last_questions = questions
        return [
            ChoiceAnswer(id=q.id, choice=self.choices[q.id][0], confidence=self.choices[q.id][1])
            for q in questions
        ]


def test_system_one_classifier_returns_one_pick_per_item():
    items = [
        CatalogItem(id="a", metadata={"name": "Alpha"}),
        CatalogItem(id="b", metadata={"name": "Beta"}),
    ]
    client = FakeChoiceClient({"a": ("Mechanical", 0.9), "b": ("Electrical", 0.7)})
    classifier = SystemOneClassifier(client=client)

    picks = classifier.classify(items, "which team owns this?", ["Mechanical", "Electrical"])

    assert set(picks) == {("a", "Mechanical", 0.9), ("b", "Electrical", 0.7)}


def test_system_one_classifier_asks_one_choice_question_per_item_with_the_given_options():
    items = [CatalogItem(id="a", metadata={}), CatalogItem(id="b", metadata={})]
    client = FakeChoiceClient({"a": ("X", 1.0), "b": ("Y", 1.0)})
    classifier = SystemOneClassifier(client=client)

    classifier.classify(items, "pick one", ["X", "Y"])

    assert len(client.last_questions) == 2
    assert all(isinstance(q, ChoiceQuestion) for q in client.last_questions)
    assert all(q.options == ["X", "Y"] for q in client.last_questions)
    # Each item's own id must be embedded in its statement, so a System One
    # model evaluating the whole catalog as shared state can tell which
    # question is about which item.
    assert client.last_questions[0].statement == "For item 'a': pick one"
    assert client.last_questions[1].statement == "For item 'b': pick one"
