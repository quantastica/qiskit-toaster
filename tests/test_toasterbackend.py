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
        

    def test_bell_counts(self):
        shots = 256
        qc=TestToasterBackend.get_bell_qc()

        backend = ToasterBackend.ToasterBackend()
        job = execute(qc, backend=backend, shots=shots)
        job_result = job.result()
        counts = job_result.get_counts(qc)
        total_counts = 0
        for c in counts:
            total_counts += counts[c]
        self.assertEqual( len(counts), 2)
        self.assertEqual( total_counts, shots)

    def test_bell_state_vector(self):
        """
        This is test for statevector which means that 
        even with shots > 1 it should execute only one shot
        """
        shots = 256
        qc=TestToasterBackend.get_bell_qc()

        backend = ToasterBackend.ToasterBackend(backend_name="statevector_simulator")
        job = execute(qc, backend=backend, shots=shots)
        job_result = job.result()
        counts = job_result.get_counts(qc)
        total_counts = 0
        for c in counts:
            total_counts += counts[c]
        self.assertEqual( len(counts), 1)
        self.assertEqual( total_counts, 1)

    @staticmethod
    def get_bell_qc():
        qc = QuantumCircuit(name="Bell")

        q = QuantumRegister(2, 'q')
        c = ClassicalRegister(2, 'c')

        qc.add_register(q)
        qc.add_register(c)

        qc.h(q[0])
        qc.cx(q[0], q[1])
        qc.measure(q[0], c[0])
        qc.measure(q[1], c[1])

        return qc        


if __name__ == '__main__':
    unittest.main()