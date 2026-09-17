from tools.translate_full_catalog import split_sentence, job_parts, prepare


def test_sentence_jobs_include_the_paragraph_ending_without_merging():
    source = 'You draw your sword. The woman steps back. She points at %protectee%. Do not let her escape!'
    segments = split_sentence(source)
    assert ''.join(segments) == source
    assert segments == ['You draw your sword.', ' The woman steps back.', ' She points at %protectee%.', ' Do not let her escape!']
    assert job_parts(source,{}) == [(False, part) for part in segments]


def test_long_clause_splitting_is_lossless_and_bounded():
    source = ' ' + ('A long sentence with a comma, and some more words ' * 18) + '.'
    segments = split_sentence(source)
    assert ''.join(segments) == source
    assert max(map(len,segments)) <= 250


def test_reviewed_whole_paragraph_keeps_priority_over_splitting():
    source = 'He nods. You leave.'
    assert job_parts(source,{source:'他点了点头。你离开了。'}) == [(True,'他点了点头。你离开了。')]
    assert prepare('A sellsword helps two sellswords.')[0] == 'A mercenary helps two mercenaries.'
