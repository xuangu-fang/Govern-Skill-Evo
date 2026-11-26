import json
import socket

import pytest

from src.adapters.officeqa.local import LocalDocuments, aligned_item, source_references
from skillopt.envs.officeqa import tool_runtime


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Network is forbidden in offline tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def url(year, page=2):
    return f'https://fraser.stlouisfed.org/title/treasury-bulletin-407/march-{year}-123?page={page}'


def name(year):
    return f'treasury_bulletin_{year}_03.txt'


def test_multiple_pages_are_mapped_by_document_not_position():
    item = {'source_files':[name(2011),name(2012)],
            'source_docs':[url(2011,2),url(2011,3),url(2012,4),url(2012,5)]}
    fixed, refs, legacy = aligned_item(item)
    assert len(legacy) == 2 and len(refs) == 4
    assert legacy[1][0] == name(2012)  # Original bug: second 2011 page in 2012 file.
    assert fixed['source_files'] == [name(2011),name(2011),name(2012),name(2012)]
    assert tool_runtime._iter_oracle_refs(fixed['source_files'],fixed['source_docs']) == refs
    assert item['source_files'] == [name(2011),name(2012)]


def test_reordered_equal_length_sources():
    fixed, refs, _ = aligned_item({'source_files':[name(2011),name(2012)],
                                 'source_docs':[url(2012),url(2011)]})
    assert fixed['source_files'] == [name(2012),name(2011)]
    assert refs[0][0] == name(2012)


def test_single_file_multiple_pages_needs_no_change():
    item={'source_files':[name(2011)],'source_docs':[url(2011,2),url(2011,3)]}
    assert aligned_item(item)[0] == item


def test_url_declared_file_addition_requires_explicit_repair():
    item={'source_files':[name(2011)],'source_docs':[url(2011),url(2012)]}
    with pytest.raises(ValueError):source_references(**item)
    assert aligned_item(item)[0]['source_files'] == [name(2011),name(2012)]


@pytest.mark.parametrize('files,docs',[
    ([],[url(2011)]),([name(2011)],[]),
    ([name(2011)],[url(2011,0)]),
    ([name(2011)],[url(2011).replace('fraser.stlouisfed.org','example.com')]),
    (['../'+name(2011)],[url(2011)]),
    ([name(2011),name(2012)],[url(2011)]),
])
def test_ambiguous_or_invalid_references_fail(files,docs):
    with pytest.raises(ValueError):source_references(files,docs)


@pytest.fixture
def corpus(tmp_path):
    parsed=tmp_path/'parsed';text=parsed/'transformed';text.mkdir(parents=True)
    (parsed/'jsons').mkdir()
    (text/name(2011)).write_text('MiXeD [literal] text\n'*1000)
    (text/name(2012)).write_text('not allowed for this task\n')
    item={'source_files':[name(2011)],'source_docs':[url(2011)]}
    return parsed,item


def test_tool_scope_literal_search_and_limits(corpus):
    parsed,item=corpus;docs=LocalDocuments(parsed,item);path=docs.paths[0]
    assert docs.call('glob',{'pattern':'*.txt'})[1] == path
    assert len(docs.call('read',{'path':path,'limit':1000})[1]) == 4000
    assert len(docs.call('grep',{'path':path,'pattern':'MIXED [literal]'})[1].splitlines()) == 20
    assert docs.call('grep',{'path':path,'pattern':'MIXED.*'})[1] == '[no matches]'
    other=str(parsed/'transformed'/name(2012))
    assert 'path not allowed' in docs.call('read',{'path':other})[1]
    assert 'path not allowed' in docs.call('grep',{'path':other,'pattern':'not'})[1]
    with pytest.raises(ValueError):docs.call('python',{})


def test_missing_empty_and_symlink_sources_fail_closed(corpus,tmp_path):
    parsed,item=corpus
    for files in ([],['missing.txt'],['../outside.txt']):
        with pytest.raises(ValueError):LocalDocuments(parsed,{'source_files':files})
    outside=tmp_path/'outside.txt';outside.write_text('secret')
    target=parsed/'transformed'/'linked.txt';target.symlink_to(outside)
    with pytest.raises(ValueError):LocalDocuments(parsed,{'source_files':['linked.txt']})


def test_oracle_pages_validate_and_render_tables(corpus):
    parsed,item=corpus;docs=LocalDocuments(parsed,item)
    with pytest.raises(ValueError):docs.pages(item)
    path=parsed/'jsons'/'treasury_bulletin_2011_03.json'
    path.write_text(json.dumps({'document':{'elements':[
        {'bbox':[{'page_id':2}],'content':'<table><tr><th>Year</th><th>Value</th></tr><tr><td>2011</td><td>10</td></tr></table>'},
        {'bbox':[{'page_id':3}],'content':'OTHER PAGE'},
    ]}}))
    context=docs.pages(item)
    assert '| Year | Value |' in context and 'OTHER PAGE' not in context
    with pytest.raises(ValueError):docs.pages({**item,'source_docs':[url(2011,4)]})


def test_network_guard_blocks_before_connect():
    from scripts.benchmarks.officeqa.prepare import deny_network, NETWORK_ATTEMPTS
    try:
        with pytest.raises(RuntimeError):deny_network('socket.connect',())
        assert NETWORK_ATTEMPTS == ['socket.connect']
    finally:NETWORK_ATTEMPTS.clear()
