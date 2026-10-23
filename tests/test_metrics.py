from evaluation.metrics import check_answer, has_number, reciprocal_rank, recall_at_k


def test_recall_and_mrr():
    ranked = ["Pug", "Beagle", "Beagle", "Akita"]
    assert recall_at_k(ranked, ["Beagle"], 1) == 0.0
    assert recall_at_k(ranked, ["Beagle"], 2) == 1.0
    assert recall_at_k(ranked, ["Beagle", "Poodle"], 4) == 0.5
    assert reciprocal_rank(ranked, ["Beagle"]) == 0.5
    assert reciprocal_rank(ranked, ["Poodle"]) == 0.0


def test_has_number_is_exact():
    assert has_number("There are 12 breeds.", 12)
    assert not has_number("There are 112 breeds.", 12)
    assert not has_number("It weighs 12.5 kg.", 12)


def test_check_answer_types():
    assert check_answer({"type": "top"}, "Great Dane and Mastiff", {"names": ["Great Dane", "Mastiff"], "total": 2})
    assert check_answer({"type": "count"}, "มีทั้งหมด 21 สายพันธุ์", {"names": [], "total": 21})
    assert check_answer({"type": "keywords", "any_of": [["Japan", "ญี่ปุ่น"]]}, "มาจากญี่ปุ่น", None)
    assert not check_answer({"type": "offtopic", "forbidden": ["Paris"]}, "It is Paris.", None)
    assert check_answer({"type": "abstain"}, "I could not find that in the documents.", None)


def test_grounded_needs_citation_and_no_refusal():
    assert check_answer({"type": "grounded"}, "French Bulldogs suit flats [2].", None)
    assert not check_answer({"type": "grounded"}, "French Bulldogs suit flats.", None)
    assert not check_answer({"type": "grounded"}, "I could not find this [1].", None)


def test_row_values_needs_every_number():
    gold = {"names": ["Great Dane", "Yorkshire Terrier"], "values": [["7", "10"], ["11", "15"]]}
    assert check_answer({"type": "row_values"}, "เกรทเดน 7-10 ปี ส่วนยอร์กเชียร์ 11-15 ปี", gold)
    assert not check_answer({"type": "row_values"}, "เกรทเดน 7-10 ปี", gold)
