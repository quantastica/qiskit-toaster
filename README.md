# Qubit Toaster backend for Qiskit

Allows running Qiskit code on Qubit Toaster - a high performance quantum circuit simulator.

More goodies at [https://quantastica.com](https://quantastica.com)


# Install

```
pip install quantastica-qiskit-toaster
```

# Usage

Import ToasterBackend into your Qiskit code:

```
from quantastica.qiskit_toaster import ToasterBackend
```

Replace `Aer.get_backend` with `ToasterBackend.get_backend`.

# Example

```python
from qiskit import QuantumRegister, ClassicalRegister
from qiskit import QuantumCircuit, execute, Aer
from quantastica.qiskit_toaster import ToasterBackend

qc = QuantumCircuit()

q = QuantumRegister(2, "q")
c = ClassicalRegister(2, "c")

qc.add_register(q)
qc.add_register(c)

qc.h(q[0])
qc.cx(q[0], q[1])

qc.measure(q[0], c[0])
qc.measure(q[1], c[1])


# Instead:
#backend = Aer.get_backend("qasm_simulator")

# Use:
backend = ToasterBackend.get_backend("qasm_simulator")

# OR (to use statevector_simulator backend):
# backend = ToasterBackend.get_backend("statevector_simulator")

# OR (to specify custom toaster_host and toaster_port params
# default values are localhost and 8001 respectively):
# backend = ToasterBackend.get_backend(
#            "statevector_simulator",
#            toaster_host="192.168.1.2",
#            toaster_port=8888,
#        )

job = execute(qc, backend=backend)
# To speed things up a little bit qiskit's optimization can be disabled
# by setting optimization_level to 0 like following:
# job = execute(qc, backend=backend, optimization_level=0)
job_result = job.result()

print(job_result.get_counts(qc))

```


# Details

**Syntax**

`ToasterBackend.get_backend(backend_name = None)`


**Arguments**

`backend_name` can be:

- `qasm_simulator` only counts will be returned

- `statevector_simulator` both counts and state vector will be returned

If backend name is not provided then it will act as `qasm_simulator`


That's it. Enjoy! :)
