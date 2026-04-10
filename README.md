# Theory of Computation - Practice 3: Automata Simulation and Minimization

[![Institution](https://img.shields.io/badge/Institution-IPN_ESCOM-004785.svg)](#)
[![Course](https://img.shields.io/badge/Course-Theory_of_Computation-blue.svg)](#)
[![Language](https://img.shields.io/badge/Language-Python_3-yellow.svg)](#)

##  About The Project

[cite_start]This repository contains the software extension developed for **Practice 3** of the Theory of Computation course at Instituto Politécnico Nacional (ESCOM)[cite: 2, 3, 8]. [cite_start]The primary objective of this project is to extend a previous Deterministic Finite Automaton (DFA) simulator to support non-determinism, state closures, and optimization algorithms[cite: 43, 44].

This tool provides an interactive graphical interface to validate formal languages, allowing users to trace parallel execution paths, resolve $\lambda$-transitions (epsilon), and mathematically optimize existing machines.

### Authors
* **Angel Heron Garcia Osornio**
* **Alan Gabriel Ramírez Nolasco**

---

##  Core Features

The application has been upgraded with the following computational capabilities:

* [cite_start]**NFA Simulation (Non-Deterministic Finite Automata):** Supports multiple branching transitions for a single state-symbol pair[cite: 45, 48]. [cite_start]The GUI displays the active set of parallel states dynamically during string processing[cite: 58].
* [cite_start]**NFA-λ Simulation (Lambda/Epsilon Transitions):** Implements an algorithmic calculation of the $\lambda$-closure to manage spontaneous state transitions before and after reading input symbols[cite: 61, 67, 107].
* [cite_start]**Subset Construction Algorithm:** Automatically converts any given NFA or NFA-λ into a strictly equivalent DFA by grouping parallel execution paths into unified macro-states[cite: 75, 77, 82].
* [cite_start]**Hopcroft's Minimization Algorithm:** Reduces a given DFA to its minimal equivalent state configuration[cite: 109, 112]. The algorithm executes two main phases:
  1. [cite_start]Removal of unreachable states[cite: 113].
  2. [cite_start]Identification and merging of indistinguishable states via equivalence partitions[cite: 114].
* [cite_start]**Batch Testing Execution:** Allows users to import `.txt` files containing multiple strings to validate them sequentially, generating an automated acceptance/rejection report[cite: 92, 94, 95].

---

##  Getting Started

### Prerequisites
To run this application locally, you will need **Python 3.x** installed on your system. The graphical user interface is built using `tkinter`, which is typically included in standard Python distributions.

### Execution Instructions
1. Clone the repository to your local machine:
   ```bash
   git clone [https://github.com/AngelGAOS/PRACTICA_3-complete.git](https://github.com/AngelGAOS/PRACTICA_3-complete.git)