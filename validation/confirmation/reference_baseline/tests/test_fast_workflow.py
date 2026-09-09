import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
from evidence_io import atomic_npz,sha256,verify_bundle
from research_gates import REQUIRED_GATES,GateClosedError
from runtime_safety import atomic_json
ROOT=Path(__file__).resolve().parents[1]


def load():
    spec=importlib.util.spec_from_file_location('fast_workflow_test',ROOT/'workflows/measure_conditioned_fast.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def fixture(tmp_path):
    evidence=tmp_path/'TEST_ONLY.txt';evidence.write_text('Artificial gate fixture; not approval')
    gates=tmp_path/'gates.json'
    atomic_json(gates,{k:{'status':'PASS','evidence':[{'path':evidence.name,'sha256':sha256(evidence)}]}
                       for k in REQUIRED_GATES})
    geom=tmp_path/'g.npz';np.savez(geom,neighbors=np.array([[j for j in range(5) if j!=i] for i in range(5)]))
    labels=tmp_path/'labels.npz';a=np.arange(5)<2
    np.savez(labels,regular=a,singular=~a,geometry_sha256=sha256(geom),
             mapping_definition='TEST_ONLY synthetic split',validation_status='VALIDATED')
    output=tmp_path/'out.npz'
    return [str(geom),str(labels),'--root',str(tmp_path),'--gates',str(gates),'--output',str(output),
            '--steps','12','--probes','32'],output,labels


def test_closed_before_read(tmp_path):
    gates=tmp_path/'gates.json';atomic_json(gates,{})
    with pytest.raises(GateClosedError):load().main(['missing','missing2','--gates',str(gates),
                                                   '--root',str(tmp_path),'--output',str(tmp_path/'o.npz')])


def test_cache_and_tamper_detection(tmp_path,capsys):
    args,out,_=fixture(tmp_path);mod=load();mod.main(args)
    assert json.loads(capsys.readouterr().out)['status']=='STOCHASTIC_MEASUREMENT_COMPLETE'
    before=out.read_bytes();mod.main(args+['--batch-size','3'])
    assert json.loads(capsys.readouterr().out)['status']=='SKIP_VERIFIED'
    assert before==out.read_bytes()
    out.write_bytes(before+b'corruption')
    with pytest.raises(RuntimeError,match='provenance'):mod.main(args)


def test_experimental_mapping_and_budget_rejected(tmp_path):
    args,out,labels=fixture(tmp_path)
    with pytest.raises(MemoryError):load().main(args+['--max-bytes','1'])
    assert not out.exists()
    with np.load(labels) as d:values={k:d[k].copy() for k in d.files}
    values['validation_status']='EXPERIMENTAL'
    np.savez(labels,**values)
    with pytest.raises(ValueError,match='VALIDATED'):load().main(args)


def test_atomic_immutable_npz_and_bundle(tmp_path):
    p=tmp_path/'a.npz';atomic_npz(p,a=np.arange(3));before=p.read_bytes()
    with pytest.raises(FileExistsError):atomic_npz(p,a=np.arange(4))
    assert p.read_bytes()==before
    atomic_json(tmp_path/'manifest.json',{'contract':{'sources':{}},'artifacts':{'a.npz':sha256(p)}})
    assert verify_bundle(tmp_path)['artifacts']['a.npz']==sha256(p)
    p.write_bytes(b'bad')
    with pytest.raises(RuntimeError):verify_bundle(tmp_path)
