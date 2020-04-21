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
# default values are 127.0.0.1 and 8001 respectively):
# backend = ToasterBackend.get_backend(
#            "statevector_simulator",
#            toaster_host="192.168.1.2",
#            toaster_port=8888,
#        )

# OR (to use it directly via CLI instead of HTTP API)
# backend = ToasterBackend.get_backend(
#            "qasm_simulator",
#            use_cli=True)

job = execute(qc, backend=backend)
# To speed things up a little bit qiskit's optimization can be disabled
# by setting optimization_level to 0 like following:
#   job = execute(qc, backend=backend, optimization_level=0)
#
# To pass different optimization level to qubit-toaster use backend_options:
#   options = { "toaster_optimization": 3 }
#   job = execute(qc, backend=backend, backend_options=options)

job_result = job.result()

print(job_result.get_counts(qc))

```


# Details

## Syntax

```
ToasterBackend.get_backend( backend_name = None,
                            toaster_host=None, 
                            toaster_port=None, 
                            use_cli=False)
```


### Arguments

- `backend_name` can be:
  - `qasm_simulator` only counts will be returned
  - `statevector_simulator` both counts and state vector will be returned
  - If backend name is not provided then it will act as `qasm_simulator`
- `toaster_host` - ip address of machine running `qubit-toaster` simulator
- `toaster_port` - port that `qubit-toaster` is listening on
- `use_cli` - if this param is set to `True` the `qubit-toaster` will be used directly (by invoking it as executable) instead via HTTP API. For this to work the `qubit-toaster` binary must be available somewhere in system PATH

### Toaster's backend_options
  - `toaster_optimization` - integer from 0 to 7
    - 0 - automatic optimization
    - 1 - optimization is off
    - 7 - highest optimization

## Running unit tests

First start `qubit-toaster` in HTTP API mode:
```
qubit-toaster -S
```

 Running standard set of tests (excluding the slow ones):
 ```
 python -m unittest -v
 ```

Running all tests (including the slow ones):
```
SLOW=1 python -m unittest -v
```

Specifying different toaster host/port:
```
TOASTER_HOST=192.168.1.2 TOASTER_PORT=8001  python -m unittest -v -f
```

Running tests by using CLI interface instead of HTTP:
```
USE_CLI=1 python -m unittest -v -f
```

-------

That's it. Enjoy! :)
