import unittest
import warnings
from quantastica.qiskit_toaster import ToasterBackend
from qiskit import QuantumRegister, ClassicalRegister
from qiskit import QuantumCircuit, execute

class TestToasterBackend(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass
        

    def test_bell(self):
        qc = QuantumCircuit(name="Bell")

        q = QuantumRegister(2, 'q')
        c = ClassicalRegister(2, 'c')

        qc.add_register(q)
        qc.add_register(c)

        qc.h(q[0])
        qc.cx(q[0], q[1])
        qc.measure(q[0], c[0])
        qc.measure(q[1], c[1])

        backend = ToasterBackend.ToasterBackend()
        job = execute(qc, backend=backend, shots=256)
        job_result = job.result()
        counts = job_result.get_counts(qc)
        self.assertTrue( len(counts) >= 1)
        


if __name__ == '__main__':
    unittest.main()