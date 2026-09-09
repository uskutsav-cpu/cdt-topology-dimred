"""CLI tests use explicitly artificial evidence, never real gate certification."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
from research_gates import REQUIRED_GATES, GateClosedError
from runtime_safety import atomic_json
ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('conditioned_workflow_test',ROOT/'workflows/measure_conditioned.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_closed_gates_before_input_read(tmp_path):
    gates = tmp_path/'gates.json'
    atomic_json(gates,{})
    output = tmp_path/'out.npz'
    with pytest.raises(GateClosedError):
        load().main(['missing.npz','missing-labels.npz','--root',str(tmp_path),
                     '--gates',str(gates),'--output',str(output)])
    assert not output.exists()


def fixture(tmp_path):
    evidence = tmp_path/'TEST_ONLY.txt'
    evidence.write_text('Artificial workflow fixture; NOT scientific approval.')
    h = hashlib.sha256(evidence.read_bytes()).hexdigest()
    gates = tmp_path/'gates.json'
    atomic_json(gates,{k:{'status':'PASS','evidence':[{'path':evidence.name,'sha256':h}]} for k in REQUIRED_GATES})
    geometry = tmp_path/'geometry.npz'
    np.savez(geometry,neighbors=np.array([[j for j in range(5) if j!=i] for i in range(5)]))
    gh = hashlib.sha256(geometry.read_bytes()).hexdigest()
    labels = tmp_path/'labels.npz'
    a = np.arange(5)<2
    np.savez(labels,regular=a,singular=~a,geometry_sha256=gh,mapping_definition='TEST_ONLY arbitrary split')
    output = tmp_path/'out.npz'
    args = [str(geometry),str(labels),'--root',str(tmp_path),'--gates',str(gates),
            '--output',str(output),'--steps','12','--block-size','2']
    return args,output,labels


def test_reference_cli_and_no_repeat(tmp_path,capsys):
    args,output,labels = fixture(tmp_path)
    mod = load()
    mod.main(args)
    assert json.loads(capsys.readouterr().out)['status'] == 'MEASUREMENT_COMPLETE'
    before = output.read_bytes()
    mod.main(args)
    assert json.loads(capsys.readouterr().out)['status'] == 'SKIP_VERIFIED'
    assert output.read_bytes() == before
    with np.load(output) as f:
        assert np.allclose(f['P_all'],f['counts']/5 @ f['P_class'])


def test_reference_budget_and_wrong_mapping(tmp_path):
    args,output,labels = fixture(tmp_path)
    with pytest.raises(RuntimeError,match='exceeds budget'):
        load().main(args+['--max-scalar-updates','1'])
    assert not output.exists()
    a = np.arange(5)<2
    np.savez(labels,regular=a,singular=~a,geometry_sha256='wrong',mapping_definition='TEST_ONLY')
    with pytest.raises(ValueError,match='different geometry'):
        load().main(args)
