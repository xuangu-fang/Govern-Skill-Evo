import datetime
import importlib.util
import sys
from pathlib import Path
import zipfile
import pytest
import openpyxl
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench import scoring,protocol




def reference_modules():
    spec=importlib.util.spec_from_file_location('skillopt_sheet_reference',Path(__file__).parent/'references/skillopt_evaluator.py')
    opt=importlib.util.module_from_spec(spec);spec.loader.exec_module(opt)
    from skilladam.benchmarks.spreadsheetbench import evaluation as adam
    return opt,adam


@pytest.mark.parametrize('left,right',[(1,'1.00'),(1.234,1.23),(1.235,1.23),(True,1),(None,''),('1,000',1000),('Text','text'),(datetime.datetime(2024,1,1),45292),(datetime.time(12,30,20),'12:30'),(None,None),(float('inf'),'inf'),(' 2 ',2)])
def test_value_comparison_against_both_repositories(left,right):
    opt,adam=reference_modules()
    assert scoring.equal(left,right)==opt._compare_cell_value(left,right)==adam.compare_cell_value(left,right)


def books(tmp_path):
    w=openpyxl.Workbook();s=w.active;s.title='Data';s.append([1,'2','same']);s.append([3,4,None]);w.create_sheet('Extra')['A1']=True
    w.save(tmp_path/'gold.xlsx');s['B2']=9;w.save(tmp_path/'pred.xlsx');w.close()
    return tmp_path/'pred.xlsx',tmp_path/'gold.xlsx'


def test_multiple_ranges_and_missing_sheet(tmp_path):
    opt,adam=reference_modules();pred,gold=books(tmp_path);region="'Data'!A1:C2,'Extra'!A1"
    ours=scoring.score(pred,gold,region,protocol.DEFAULTS);theirs=adam.compare_workbooks(pred,gold,region)
    assert ours['hard']==opt.compare_workbooks(str(gold),str(pred),region)[0]==theirs['ok']==False
    assert ours['correct_cells']==theirs['n_cells_match']==6
    assert ours['total_cells']==theirs['n_cells_total']==7
    assert ours['per_cell_pass_rate']==theirs['per_cell_pass_rate']==0.8571
    w=openpyxl.load_workbook(pred);del w['Extra'];w.save(pred);w.close()
    ours=scoring.score(pred,gold,region,protocol.DEFAULTS)
    assert ours['missing_sheets']==['Extra'] and ours['correct_cells']==5


def test_saved_formula_cache_and_no_recalculation(tmp_path):
    w=openpyxl.Workbook();w.active.title='Data';w.active['A1']=3;w.save(tmp_path/'gold.xlsx');w.active['A1']='=1+2';w.save(tmp_path/'formula.xlsx');w.close()
    region='Data!A1';raw=scoring.score(tmp_path/'formula.xlsx',tmp_path/'gold.xlsx',region,protocol.DEFAULTS)
    assert raw['hard']==0
    with zipfile.ZipFile(tmp_path/'formula.xlsx') as original,zipfile.ZipFile(tmp_path/'cached.xlsx','w') as out:
        for item in original.infolist():
            value=original.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':value=value.replace(b'<v></v>',b'<v>3</v>').replace(b'<v />',b'<v>3</v>').replace(b'<v/>',b'<v>3</v>')
            out.writestr(item,value)
    assert scoring.score(tmp_path/'cached.xlsx',tmp_path/'gold.xlsx',region,protocol.DEFAULTS)['hard']==1


def test_score_projection_caps_without_expected_values(tmp_path):
    w=openpyxl.Workbook();w.active.title='Data'
    for i in range(1,151):w.active.cell(i,1).value='PRIVATE_EXPECTED'
    w.save(tmp_path/'gold.xlsx');w.close()
    result=scoring.score(None,tmp_path/'gold.xlsx','Data!A1:A150',protocol.DEFAULTS)
    view=scoring.model_view(result,protocol.DEFAULTS)
    assert len(view['mismatched_cells'])==100 and view['mismatched_cells_total']==150
    assert 'PRIVATE_EXPECTED' not in str(view)


@pytest.mark.parametrize('region',["Sheet3'!A:G,'Sheet4'!A:G","'Sheet1'!BD2:308"])
def test_known_metadata_issues_are_compatible_without_upstream_false_pass(region):
    opt,adam=reference_modules()
    parsed=scoring.regions(region)
    cell=region.split(',')[0].split('!')[1].strip("'")
    if cell=='BD2:308':
        assert opt._generate_cell_names(cell)==[]
        assert parsed==[('Sheet1',(56,2,56,308))]
    else:
        assert parsed==[('Sheet3',(1,1,7,None)),('Sheet4',(1,1,7,None))]
        with pytest.raises((ValueError,AttributeError)):opt._generate_cell_names(cell)
    with pytest.raises(ValueError):adam.expand_cells(cell)


def test_dataset_loose_quotes_parse_like_references():
    opt,adam=reference_modules();region="'Sheet1!'A1:A50,'Sheet2!'A1:E20,'Sheet3!'A1:A50'"
    ours=scoring.regions(region)
    assert [s for s,b in ours]==['Sheet1','Sheet2','Sheet3']
    assert sum((b[2]-b[0]+1)*(b[3]-b[1]+1) for s,b in ours)==200
    for raw,(sheet,bounds) in zip(region.split(','),ours):
        name,cells=adam._split_reference(raw,answer_sheet='',default_sheet='Sheet1')
        assert name==sheet and len(adam.expand_cells(cells))==len(opt._generate_cell_names(cells))


def test_comma_in_sheet_name_preserved():
    assert scoring.regions("'b2b, sez, de'!A5:V10")==[('b2b, sez, de',(1,5,22,10))]
    # A multi-name field is not silently expanded to multiple worksheets.
    assert len(scoring.regions("'Consolidated Tracker,Existing Task,Additions,Retired'!A3:E11"))==1


def test_whole_columns_include_extra_prediction_rows_and_missing_sheet(tmp_path):
    w=openpyxl.Workbook();w.active.title='Sheet3';w.active['A1']='expected';w.save(tmp_path/'gold.xlsx')
    w.active['G8']='extra';w.save(tmp_path/'pred.xlsx');w.close()
    result=scoring.score(tmp_path/'pred.xlsx',tmp_path/'gold.xlsx','Sheet3!A:G',protocol.DEFAULTS)
    assert result['hard']==0 and result['total_cells']==56 and result['correct_cells']==55
    assert result['mismatched_cells']==['Sheet3!G8']
    missing=scoring.score(None,tmp_path/'gold.xlsx','Sheet3!A:G',protocol.DEFAULTS)
    assert missing['hard']==0 and missing['total_cells']==7


def test_shorthand_compares_cells_instead_of_vacuous_pass(tmp_path):
    w=openpyxl.Workbook();w.active.title='Sheet1';w.active['BD308']='expected';w.save(tmp_path/'gold.xlsx')
    w.active['BD308']='wrong';w.save(tmp_path/'pred.xlsx');w.close()
    result=scoring.score(tmp_path/'pred.xlsx',tmp_path/'gold.xlsx',"'Sheet1'!BD2:308",protocol.DEFAULTS)
    assert result['hard']==0 and result['total_cells']==307
    assert result['mismatched_cells']==['Sheet1!BD308']


@pytest.mark.parametrize('region',['Data!G:A','Data!BD308:2','Data!1:3','Data!A0:A2','Data!'])
def test_compatibility_does_not_accept_empty_or_reversed_ranges(region):
    with pytest.raises(ValueError):scoring.regions(region)


def test_rounded_and_historical_rates_both_pass_fact_audit(tmp_path):
    from .support import config,ActorResponses,fast_execute,PARENT
    from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench import actor,facts
    import json
    c=config(tmp_path/'data',n=1);t=next(iter(c['task_items'].values()));t['answer_region']='Sheet1!A1:C3'
    path=actor.run(t,PARENT,tmp_path/'actor',c,generate=ActorResponses(),execute=fast_execute)
    record=json.loads(path.read_text());assert record['score']['per_cell_pass_rate']==0.8889
    facts.build_facts([record])
    record['score']['per_cell_pass_rate']=8/9;facts.build_facts([record])
    record['score']['per_cell_pass_rate']=0.889
    with pytest.raises(ValueError,match='Score counts/rates differ'):facts.build_facts([record])
