"""Run on a machine that has qiskit + Aer + IBM runtime installed."""
import importlib.util
import unittest
from src.simulation.noise import load_backends, load_circuits, run_simulation

HAS_QISKIT = all(importlib.util.find_spec(x) is not None
                 for x in ("qiskit", "qiskit_aer", "qiskit_ibm_runtime"))


@unittest.skipUnless(HAS_QISKIT, "Requires Qiskit + Aer + IBM runtime")
class TestQiskitIntegration(unittest.TestCase):
    def test_loading(self):
        self.assertEqual(len(load_backends()), 4)
        self.assertEqual(len(load_circuits("data/circuits")), 10)

    def test_small_simulation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            runs, summary = run_simulation(shots=128, seeds=(42,), output_dir=tmp,
                                           backend_names=("fake_manila",))
            self.assertEqual(len(runs), 10)
            self.assertEqual(len(summary), 10)
            self.assertTrue(runs.distribution_fidelity.between(0, 1).all())


if __name__ == '__main__':
    unittest.main()
