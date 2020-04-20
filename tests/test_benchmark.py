from qiskit import Aer, QuantumCircuit, execute
from qiskit.compiler import transpile, assemble
from quantastica.qiskit_toaster import ToasterBackend
import time
import logging
import os

backend = ToasterBackend.get_backend("qasm_simulator")
# backend = Aer.get_backend("qasm_simulator")
default_options = {
    # "method": "statevector",   # Force dense statevector method for benchmarks
    # "truncate_enable": False,  # Disable unused qubit truncation for benchmarks
    # "max_parallel_threads": 1,  # Disable OpenMP parallelization for benchmarks
    "toaster_optimization": 3  # optimization for qubit-toaster
}

# def _execute(circuit, backend_options=None):
#     experiment = transpile(circuit, backend)
#     qobj = assemble(experiment, shots=1)
#     qobj_aer = backend._format_qobj(qobj, backend_options, None)
#     return backend._controller(qobj_aer)


def _execute(circuit, backend):
    job = execute(circuit, backend=backend)
    # job.result is needed in order to wait for results
    job.result()


def native_execute(benchmark, circuit, backend_options=None):
    # experiment = transpile(circuit, backend)
    # qobj = assemble(experiment, shots=1)
    # qobj_aer = backend._format_qobj(qobj, backend_options, None)
    # benchmark(backend._controller, qobj_aer)
    benchmark(_execute, circuit, backend)


def run_bench(benchmark, nqubits, gate, locs=(1,)):
    qc = QuantumCircuit(nqubits)
    getattr(qc, gate)(*locs)
    native_execute(benchmark, qc, default_options)


def first_rotation(circuit, nqubits):
    circuit.rx(1.0, range(nqubits))
    circuit.rz(1.0, range(nqubits))
    return circuit


def mid_rotation(circuit, nqubits):
    circuit.rz(1.0, range(nqubits))
    circuit.rx(1.0, range(nqubits))
    circuit.rz(1.0, range(nqubits))
    return circuit


def last_rotation(circuit, nqubits):
    circuit.rz(1.0, range(nqubits))
    circuit.rx(1.0, range(nqubits))
    return circuit


def entangler(circuit, pairs):
    for a, b in pairs:
        circuit.cx(a, b)
    return circuit


def generate_qcbm_circuit(nqubits, depth, pairs):
    circuit = QuantumCircuit(nqubits)
    first_rotation(circuit, nqubits)
    entangler(circuit, pairs)
    for k in range(depth - 1):
        mid_rotation(circuit, nqubits)
        entangler(circuit, pairs)
    last_rotation(circuit, nqubits)
    # circuit.measure_all()
    return circuit


def test_qcbm(name, backend, nqubits, optimization_level=None):
    pairs = [(i, (i + 1) % nqubits) for i in range(nqubits)]
    circuit = generate_qcbm_circuit(nqubits, 9, pairs)
    with open("circuit.qasm", "w") as f:
        f.write(circuit.qasm())
    t1 = time.time()

    # test = transpile(circuit, optimization_level=0)
    # qobj = assemble(circuit)
    # job = backend.run(qobj, backend_options=default_options)

    job = execute(
        circuit,
        backend=backend,
        backend_options=default_options,
        optimization_level=optimization_level,
    )

    # job.result is needed in order to wait for results
    result = job.result()
    t2 = time.time()
    # print(result)
    # counts = result.get_counts(circuit)
    # print("Counts size: %d" % len(counts))
    print("  %s time: %f" % (name, t2 - t1))


if __name__ == "__main__":
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(pathname)s - %(message)s",
        level=os.environ.get("LOGLEVEL", "CRITICAL"),
    )
    N = int(os.environ.get("N", 20))
    LOOPS = int(os.environ.get("LOOPS", 10))
    for i in range(0, LOOPS):
        print("Iteration #%d (of %d)" % (i, LOOPS))
        test_qcbm("AER", Aer.get_backend("qasm_simulator"), N, 0)
        test_qcbm(
            "TOASTER", ToasterBackend.get_backend("qasm_simulator"), N, 0
        )
