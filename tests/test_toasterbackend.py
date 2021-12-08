import unittest
from qiskit import QuantumRegister, ClassicalRegister
from qiskit import QuantumCircuit, execute
from qiskit.providers.aer import AerSimulator
from math import pi

try:
    from . import common
except Exception:
    import common


class TestToasterBackend(common.TestToasterBase):
    def test_bell_counts(self):
        shots = 256
        qc = TestToasterBackend.get_bell_qc()
        stats = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(), qc, shots
        )
        self.assertTrue(stats["statevector"] is None)
        self.assertEqual(len(stats["counts"]), 2)
        self.assertEqual(stats["totalcounts"], shots)

    def test_bell_counts_with_seed(self):
        shots = 1024
        qc = TestToasterBackend.get_bell_qc()
        stats1 = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(), qc, shots, seed=1
        )
        stats2 = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(), qc, shots, seed=1
        )
        stats3 = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(), qc, shots, seed=2
        )
        self.assertTrue(stats1["statevector"] is None)
        self.assertEqual(len(stats1["counts"]), 2)
        self.assertEqual(stats1["totalcounts"], shots)
        self.assertEqual(stats1["counts"], stats2["counts"])
        self.assertNotEqual(stats1["counts"], stats3["counts"])

    def test_teleport_counts(self):
        shots = 256
        qc = TestToasterBackend.get_teleport_qc()
        stats = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(), qc, shots
        )
        self.assertTrue(stats["statevector"] is None)
        self.assertEqual(stats["totalcounts"], shots)
        self.assertEqual(len(stats["counts"]), 4)

    def test_bell_state_vector(self):
        """
        This is test for statevector which means that
        even with shots > 1 it should execute only one shot
        """
        shots = 256
        qc = TestToasterBackend.get_bell_qc()
        stats = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(backend_name="statevector_simulator"),
            qc,
            shots,
        )
        self.assertEqual(len(stats["statevector"]), 4)
        self.assertEqual(len(stats["counts"]), 1)
        self.assertEqual(stats["totalcounts"], 1)

    def test_teleport_state_vector(self):
        """
        This is test for statevector which means that
        even with shots > 1 it should execute only one shot
        """
        shots = 256
        qc = TestToasterBackend.get_teleport_qc()

        """
        Let's first run the aer simulation to get statevector
        and counts so we can compare those results against forest's
        """
        qc_for_aer = qc.copy()
        qc_for_aer.save_state()
        stats_aer = TestToasterBackend.execute_and_get_stats(
            AerSimulator(method="statevector"), qc_for_aer, shots
        )
        """
        Now execute toaster backend
        """
        stats = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(backend_name="statevector_simulator"),
            qc,
            shots,
        )
        self.assertEqual(len(stats["counts"]), 1)
        self.assertEqual(stats["totalcounts"], 1)
        self.assertEqual(
            len(stats["statevector"]), len(stats_aer["statevector"])
        )

        """
        Let's verify that tests are working as expected
        by running fail case
        """
        stats = TestToasterBackend.execute_and_get_stats(
            self.toaster_backend(), qc, shots
        )
        self.assertTrue(stats["statevector"] is None)


    def test_multiple_jobs(self):
        qc = self.get_bell_qc()
        backend = self.toaster_backend()
        jobs = []
        for i in range(1, 50):
            jobs.append(execute(qc, backend=backend, shots=1))
        for job in jobs:
            result = job.result()
            counts = result.get_counts(qc)
            self.assertEqual(len(counts), 1)

    def test_multiple_experiments(self):
        backend = self.toaster_backend()
        qc_list = [self.get_bell_qc(), self.get_teleport_qc()]
        job_info = backend.run(qc_list)
        bell_counts = job_info.result().get_counts("Bell")
        tel_counts = job_info.result().get_counts("Teleport")
        self.assertEqual(len(bell_counts), 2)
        self.assertEqual(len(tel_counts), 4)

    def test_too_many_qubits(self):
        qc = QuantumCircuit(name="TooManyQubits")

        q = QuantumRegister(100, "q")
        qc.add_register(q)

        with self.assertRaises(RuntimeError):
            TestToasterBackend.execute_and_get_stats(
                self.toaster_backend(), qc, 1
            )

    def test_larger_circuit_statevector(self):
        n = 19
        qc = QuantumCircuit()
        q = QuantumRegister(n, 'q')
        #c = ClassicalRegister(n, 'c')
        qc.add_register(q)
        #qc.add_register(c)
        for i in range(n):
            qc.h(i)
        TestToasterBackend.execute_and_get_stats(
            self.toaster_backend('statevector_simulator'), qc, 1
        )

    @classmethod
    def execute_and_get_stats(cls, backend, qc, shots, seed=None):
        job = execute(qc, backend=backend, shots=shots, seed_simulator=seed)
        job_result = job.result()
        counts = job_result.get_counts(qc)
        total_counts = 0
        for c in counts:
            total_counts += counts[c]

        try:
            state_vector = job_result.get_statevector(qc)
        except Exception:
            state_vector = None
        ret = dict()
        ret["counts"] = counts
        ret["statevector"] = state_vector
        ret["totalcounts"] = total_counts
        return ret

    @staticmethod
    def get_bell_qc():
        qc = QuantumCircuit(name="Bell")

        q = QuantumRegister(2, "q")
        c = ClassicalRegister(2, "c")

        qc.add_register(q)
        qc.add_register(c)

        qc.h(q[0])
        qc.cx(q[0], q[1])
        qc.measure(q[0], c[0])
        qc.measure(q[1], c[1])
        return qc

    @staticmethod
    def get_teleport_qc():
        qc = QuantumCircuit(name="Teleport")

        q = QuantumRegister(3, "q")
        c0 = ClassicalRegister(1, "c0")
        c1 = ClassicalRegister(1, "c1")

        qc.add_register(q)
        qc.add_register(c0)
        qc.add_register(c1)

        qc.rx(pi / 4, q[0])
        qc.h(q[1])
        qc.cx(q[1], q[2])
        qc.cx(q[0], q[1])
        qc.h(q[0])
        qc.measure(q[1], c1[0])
        qc.x(q[2]).c_if(c1, 1)
        qc.measure(q[0], c0[0])
        qc.z(q[2]).c_if(c0, 1)
        return qc

if __name__ == "__main__":
    unittest.main()
