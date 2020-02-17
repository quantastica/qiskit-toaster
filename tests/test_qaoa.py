import unittest
import networkx as nx
import numpy as np
from docplex.mp.model import Model

from qiskit import BasicAer
from qiskit.aqua import aqua_globals, QuantumInstance
from qiskit.aqua.algorithms import QAOA
from qiskit.aqua.components.optimizers import SPSA
from qiskit.optimization.ising import docplex, max_cut
from qiskit.optimization.ising.common import sample_most_likely
from quantastica.qiskit_toaster import ToasterBackend, ToasterJob


import time
import sys
import logging
import os


@unittest.skipUnless(
    os.getenv("SLOW") == "1",
    "Skipping this test (environment variable SLOW must be set to 1)",
)
class TestQAOA(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            format='%(levelname)s %(asctime)s %(pathname)s - %(message)s',
            level=os.environ.get("LOGLEVEL", "CRITICAL"),
        )
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        sys.stderr.write(" took %.3fs ... " % (t))

    def test_qaoa(self):
        print("Running toaster test...")
        toaster_backend = ToasterBackend.get_backend("qasm_simulator")
        toaster_results = self.run_simulation(toaster_backend)
        print("Convert time:",ToasterJob.ToasterJob._qconvert_time,"seconds")
        print("Toaster time:",ToasterJob.ToasterJob._qtoaster_time,"seconds")
        print("Run time:",ToasterJob.ToasterJob._run_time,"seconds")
        print("ToasterJob executed",ToasterJob.ToasterJob._execution_count,"times")
        print("Running AER test...")
        aer_backend = BasicAer.get_backend("qasm_simulator")
        aer_results = self.run_simulation(aer_backend)
        print("===== Calculations done =====")
        print("  ==== AER Results =====")
        print(aer_results)
        print("  ==== Toaster Results =====")
        print(toaster_results)
        self.assertTrue(
            np.array_equal(
                aer_results["solution"], toaster_results["solution"]
            )
        )

    def run_simulation(self, backend):
        n = 4
        graph = nx.Graph()
        graph.add_nodes_from(np.arange(0, n, 1))
        elist = [
            (0, 1, 1.0),
            (0, 2, 1.0),
            (0, 3, 1.0),
            (1, 2, 1.0),
            (2, 3, 1.0),
        ]
        graph.add_weighted_edges_from(elist)

        """
        #
        # Example graph from "Qiskit Textbook"
        #

        # Butterfly graph with 5 nodes. Solution is: 10010

        n     = 5
        graph = nx.Graph()
        graph.add_nodes_from(np.arange(0, n, 1))
        elist = [(0,1,1.0),(0,2,1.0),(1,2,1.0),(3,2,1.0),(3,4,1.0),(4,2,1.0)]
        graph.add_weighted_edges_from(elist)
        """

        """
        #
        # Example graph from Rigetti Grove
        #

        # Square graph from Rigetti's QAOA example. Solution is: 0101 or 1010

        n     = 4
        graph = nx.Graph()
        graph.add_nodes_from(np.arange(0, n, 1))
        elist = [(0,1,1.0),(1,2,1.0),(2,3,1.0),(3,0,1.0)]
        graph.add_weighted_edges_from(elist)

        """

        # Compute the weight matrix from the graph
        w = np.zeros([n, n])
        for i in range(n):
            for j in range(n):
                temp = graph.get_edge_data(i, j, default=0)
                if temp != 0:
                    w[i, j] = temp["weight"]

        # Create an Ising Hamiltonian with docplex.
        mdl = Model(name="max_cut")
        mdl.node_vars = mdl.binary_var_list(list(range(n)), name="node")
        maxcut_func = mdl.sum(
            w[i, j] * mdl.node_vars[i] * (1 - mdl.node_vars[j])
            for i in range(n)
            for j in range(n)
        )
        mdl.maximize(maxcut_func)
        qubit_op, offset = docplex.get_operator(mdl)

        # Run quantum algorithm QAOA on qasm simulator
        seed = 40598
        aqua_globals.random_seed = seed

        spsa = SPSA(max_trials=250)
        qaoa = QAOA(qubit_op, spsa, p=5, max_evals_grouped = 4)

        quantum_instance = QuantumInstance(
            backend, shots=1024, seed_simulator=seed, seed_transpiler=seed,
            optimization_level=0
        )
        result = qaoa.run(quantum_instance)

        x = sample_most_likely(result["eigvecs"][0])
        result["solution"] = max_cut.get_graph_solution(x)
        result["solution_objective"] = max_cut.max_cut_value(x, w)
        result["maxcut_objective"] = result["energy"] + offset
        """
        print("energy:", result["energy"])
        print("time:", result["eval_time"])
        print("max-cut objective:", result["energy"] + offset)
        print("solution:", max_cut.get_graph_solution(x))
        print("solution objective:", max_cut.max_cut_value(x, w))
        """
        return result


if __name__ == "__main__":
    unittest.main()
