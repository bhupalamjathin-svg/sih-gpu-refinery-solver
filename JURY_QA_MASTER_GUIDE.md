# 🎯 SIH 2026 Jury Q&A Master Guide: Technical & Non-Technical Questions
**Problem Statement SIH26119 (Ministry of Petroleum & Natural Gas - MoPNG)**  
*Project: PDHG-GPU — Indigenous GPU-Accelerated Optimization Solver for Industrial Refinery Planning*

---

## 📑 Quick Navigation
1. [Category A: Optimization & Mathematical Algorithm Questions](#category-a-optimization--mathematical-algorithm-questions)
2. [Category B: GPU Architecture, CUDA & HPC Questions](#category-b-gpu-architecture-cuda--hpc-questions)
3. [Category C: Refinery Engineering & Domain Modeling Questions](#category-c-refinery-engineering--domain-modeling-questions)
4. [Category D: Numerical Stability, Preprocessing & Edge Cases](#category-d-numerical-stability-preprocessing--edge-cases)
5. [Category E: Business Case, ROI & Economic Impact](#category-e-business-case-roi--economic-impact)
6. [Category F: Comparison Against Existing Commercial Giants](#category-f-comparison-against-existing-commercial-giants)
7. [Category G: National Security, Sovereignty & Atmanirbhar Bharat](#category-g-national-security-sovereignty--atmanirbhar-bharat)
8. [Category H: Deployment, Scalability & Long-Term Maintenance](#category-h-deployment-scalability--long-term-maintenance)

---

# CATEGORY A: Optimization & Mathematical Algorithm Questions

### Q1. Why did you choose First-Order PDHG (Chambolle-Pock) instead of the Simplex or Interior Point Method?
* **What the judge is testing:** Did you blindly pick an algorithm, or do you understand computational complexity?
* **Winning Answer:**  
  *"Simplex and Interior Point methods are fundamentally sequential. Interior Point requires factorizing $(A \Theta A^T)$ using Cholesky decomposition at every iteration, which scales at $O(N^3)$ and creates a severe memory wall. Simplex moves vertex-to-vertex via sequential basis changes. Neither maps well to thousands of parallel GPU cores.  
  In contrast, Chambolle-Pock First-Order PDHG replaces matrix inversion with alternating matrix-vector multiplications ($Ax$ and $A^T y$) and coordinate projections. Every row operation is completely independent and parallelizable across 4,600+ CUDA cores."*

---

### Q2. First-order methods are known to have slower asymptotic convergence than second-order methods. How do you guarantee precision for industrial engineering models?
* **What the judge is testing:** Precision awareness. Can your solver reach refinery-grade accuracy?
* **Winning Answer:**  
  *"Standard subgradient methods converge slowly at $O(1/\sqrt{k})$, but Chambolle-Pock PDHG achieves an optimal $O(1/k)$ rate for convex saddle-point problems. To bridge the practical gap, we implemented three key enhancements from Google's recent PDLP research:  
  1. **Ruiz diagonal preconditioning**, which drops the condition number from $10^7$ to $10^2$.  
  2. **Adaptive step-sizes ($\tau, \sigma$)** tuned to the spectral radius via power iteration.  
  3. **Adaptive restarts** whenever residual progress stalls.  
  This achieves relative KKT residuals and duality gaps below $10^{-4}$ to $10^{-6}$, which far exceeds the 0.1% tolerance needed for refinery mass balances."*

---

### Q3. How do you detect and handle Infeasible or Unbounded problems?
* **What the judge is testing:** Completeness of your solver. Real solvers don't just solve; they detect errors.
* **Winning Answer:**  
  *"We monitor the normalized homogeneous iterate $(\bar{x}/\|\bar{x}\|, \bar{y}/\|\bar{y}\|)$ based on Farkas' Lemma:  
  - If the iterates diverge such that $A^T y \le 0$ with $b^T y > 0$, it proves **primal infeasibility** (Farkas' certificate).  
  - If $Ax \ge 0$, $x \ge 0$, and $c^T x < 0$, it proves **dual infeasibility (unbounded primal)**.  
  If neither condition stabilizes and iteration limits are reached, our solver flags an `iteration_limit` or `infeasible` status code rather than returning an invalid operating point."*

---

### Q4. How do you calculate Dual Variables (Shadow Prices) without a Simplex basis matrix?
* **What the judge is testing:** Can your first-order solver provide the economic sensitivity data that refinery planners rely on?
* **Winning Answer:**  
  *"In our saddle-point minimax formulation:  
  $$\min_x \max_{y \ge 0} c^T x + y^T(Ax - b)$$  
  The dual multiplier vector $\mathbf{y}$ is an explicit primary decision variable updated at every single iteration alongside $\mathbf{x}$. When the algorithm terminates at KKT optimality, the converged vector $\mathbf{y}^*$ corresponds directly to the marginal economic shadow prices $\lambda_i = \partial \text{Margin}/\partial b_i$. We unscale this using our Ruiz diagonal factors $D$ to return exact dollar-per-barrel sensitivities."*

---

### Q5. How does your solver handle Mixed-Integer Linear Programs (MILP) on GPU?
* **What the judge is testing:** GPUs struggle with branching trees. How did you solve this?
* **Winning Answer:**  
  *"We implemented a **Heterogeneous Branch-and-Bound** architecture. Managing the tree, priority queue, and branch selection is irregular logic that runs efficiently on the **CPU**. However, evaluating each node requires solving a continuous LP relaxation.  
  The LP relaxation at each node is offloaded to the **GPU**, using warm-started primal-dual vectors from the parent node. Because the parent solution is close to the child's solution, PDHG solves each child node in just 50–100 iterations instead of thousands."*

---

### Q6. What is the difference between LP and QP in your solver?
* **What the judge is testing:** Did you just copy LP code for QP?
* **Winning Answer:**  
  *"For Linear Programs (LP), the objective gradient is constant ($\nabla f(x) = c$).  
  For Quadratic Programs (QP)—which we use for Markowitz crude procurement risk minimization—the objective contains a positive semi-definite covariance matrix ($\frac{1}{2} x^T Q x + c^T x$).  
  In our Proximal PDHG engine, the gradient step incorporates the quadratic term $\nabla f(x) = c + Qx$. Furthermore, the convergence step-size condition is tightened to $\tau(\sigma \|A\|^2 + \|Q\|) < 1$ to maintain strict numerical stability."*

---

# CATEGORY B: GPU Architecture, CUDA & HPC Questions

### Q7. What exact GPU hardware, libraries, and CUDA kernels are you using?
* **What the judge is testing:** Is your code really running on a GPU or did you just import an off-the-shelf library?
* **Winning Answer:**  
  *"Our prototype is developed and tested on an **NVIDIA GeForce RTX 4070 Laptop GPU** (Ada Lovelace architecture, compute capability 8.9, 4,608 CUDA cores, 8GB GDDR6 VRAM, 504 GB/s bandwidth).  
  We utilize **CuPy** for asynchronous CUDA array dispatch and written custom **C++ CUDA kernels** (`cuda_kernels.py`) for the inner dual clamp and primal box projection steps. The entire iterative solver loop executes in VRAM without host-device synchronization."*

---

### Q8. Did you use Float32 (single precision) or Float64 (double precision)? Why?
* **What the judge is testing:** Deep understanding of numerical linear algebra vs. GPU compute throughput.
* **Winning Answer:**  
  *"We use **Float64 (FP64)** for matrix iterates and residuals to prevent catastrophic cancellation when calculating small duality gaps ($< 10^{-6}$).  
  While consumer GPUs have higher FP32 throughput than FP64, our memory and compute profiling proved that for industrial LP, FP64 is essential for KKT precision. To optimize speed, our memory is dominated by sparse CSR access where memory bandwidth (504 GB/s) is the bottleneck, not compute FLOPs."*

---

### Q9. What happens if an industrial problem exceeds the 8GB VRAM of the GPU?
* **What the judge is testing:** Memory wall and scalability.
* **Winning Answer:**  
  *"Because we use **Compressed Sparse Row (CSR)** format, memory scales strictly with non-zeros $O(\text{NNZ})$, not matrix dimensions $O(M \times N)$. An 8GB VRAM card can store **364 million non-zero entries**, which covers a 100,000-variable model with 0.1% density hundreds of times over.  
  Furthermore, our `MemoryProfiler` (`solver/memory_profiler.py`) inspects matrix NNZ before allocation. If a model ever exceeds VRAM, it triggers a dynamic fallback to CPU multi-threaded sparse streaming."*

---

### Q10. How do you prevent PCIe bus transfer bottlenecks between CPU and GPU?
* **What the judge is testing:** Understanding of host-to-device bandwidth traps.
* **Winning Answer:**  
  *"The biggest mistake in naive GPU computing is copying data across PCIe at every iteration. In our architecture, the constraint matrix $A$ and its transpose $A^T$ are uploaded to GPU VRAM **exactly once** during initialization.  
  The entire 1,000 to 10,000 PDHG iteration loop executes **100% inside GPU memory**. We only copy a single scalar convergence metric back to CPU every 50 iterations for logging. When optimal, only the final solution vector $x^*$ is retrieved."*

---

### Q11. Why did you use Compressed Sparse Row (CSR) instead of CSC or COO?
* **What the judge is testing:** Knowledge of sparse matrix formats.
* **Winning Answer:**  
  *"Our algorithm performs two matrix-vector multiplications per step: $Ax$ (forward) and $A^T y$ (backward).  
  We store matrix $A$ in **CSR** format because CSR enables coalesced, row-parallel memory access where each CUDA warp computes a contiguous row dot-product. For $A^T y$, we pre-transpose $A$ into $A^T$ in CSR format upfront, so both forward and transpose operations achieve peak coalesced memory bandwidth without on-the-fly transposition."*

---

# CATEGORY C: Refinery Engineering & Domain Modeling Questions

### Q12. What specific refinery problem did you model, and what equations govern it?
* **What the judge is testing:** Are you computer science students playing with toy math, or do you understand petroleum refining?
* **Winning Answer:**  
  *"We modeled an integrated **8-Crude Petroleum Refinery digital twin** based on Indian Oil Corporation (IOCL Mathura) and MRPL Mangalore topologies:  
  1. **Feedstock Layer:** 8 global crudes (Bombay High, Arab Light, Arab Heavy, Bonny Light, Maya, Urals, Basrah, Murban) with real API gravity and sulfur assays.  
  2. **4-Stage Processing Units:** Atmospheric Distillation (CDU), Vacuum Distillation (VDU), Fluidized Catalytic Cracking (FCCU), Continuous Catalytic Reformer (CRU), and Diesel Hydrotreater (DHT).  
  3. **Mass Balances:** Conservation of volume across every split fraction.  
  4. **Quality Specifications:** Linearized BS-VI constraints: Petrol RON $\ge 91$, Diesel Sulfur $\le 10\text{ ppm}$, and Jet Fuel smoke point."*

---

### Q13. Refining blending equations are non-linear (e.g., Octane and Vapor Pressure blending). How can a Linear Solver (LP) handle this?
* **What the judge is testing:** Deep chemical engineering knowledge (the pooling problem).
* **Winning Answer:**  
  *"In actual refinery operations (like Aspen PIMS and Haverly GRTMPS), nonlinear quality pooling is handled via **Successive Linear Programming (SLP)** or **linear blending indices**:  
  - For Octane (RON), we use volumetric blending index numbers that behave linearly.  
  - For Sulfur (ppm), mass-fraction sulfur blurs linearly across streams.  
  Our solver accepts the linearized LP subproblem at each iteration and can be wrapped in a Frank-Wolfe or SLP loop to update blend indices dynamically."*

---

### Q14. What are 'Shadow Prices' and how does an IOCL/MRPL plant engineer use them?
* **What the judge is testing:** Can your tool provide business intelligence to refinery schedulers?
* **Winning Answer:**  
  *"A shadow price ($\lambda_i$) is the Lagrange dual multiplier corresponding to a constraint. It tells the refinery manager:  
  *‘If you increase this unit's capacity by 1 barrel/day, your daily operating margin increases by \$X.’*  
  For example, in our IOCL Mathura solved test, the Diesel Hydrotreater (DHT) showed a shadow price of **+\$27.19/bbl**, while the CDU had a shadow price of zero. This immediately tells the refinery engineer that crude distillation has slack capacity, but the hydrotreater is severely bottlenecking BS-VI diesel production. Expanding DHT capacity is where capital investment should go."*

---

### Q15. Can your solver handle multi-period scheduling with tank inventory balances?
* **What the judge is testing:** Does your model handle dynamic time horizons (7-day or 30-day schedules)?
* **Winning Answer:**  
  *"Yes. In `refinery/scheduling.py`, we implement a multi-period production scheduling formulation across $T$ time periods. It models:  
  $$\text{Inventory}_{t, k} = \text{Inventory}_{t-1, k} + \sum_u P_{t, u, k} - \text{Demand}_{t, k}$$  
  along with tank capacity bounds and inventory holding costs. We tested this on multi-period setups up to 60 periods across 8 processing units, solving in under 1.6 seconds."*

---

# CATEGORY D: Numerical Stability, Preprocessing & Edge Cases

### Q16. What is Ruiz Preconditioning and why couldn't you solve without it?
* **What the judge is testing:** Understanding of numerical ill-conditioning in industrial LP.
* **Winning Answer:**  
  *"Industrial refinery matrices combine very large numbers (e.g., CDU capacity = 160,000 bpd) with very small numbers (e.g., sulfur limit = 0.00001 mass fraction). This creates an extreme condition number $\kappa(A) \approx 10^7$, causing gradient oscillations and stalling first-order solvers.  
  **Ruiz Equilibration** iteratively computes diagonal scaling matrices $D$ and $E$ such that every row and column has an infinity norm close to 1:  
  $$A_{\text{scaled}} = D \cdot A \cdot E$$  
  This reduces the condition number to $\sim 10^2$, enabling rapid convergence in hundreds of iterations instead of tens of thousands."*

---

### Q17. How do you recover the unscaled physical solution after Ruiz scaling?
* **What the judge is testing:** Mathematical rigor in post-processing.
* **Winning Answer:**  
  *"Since $A_{\text{scaled}} = D A E$, the scaled problem variables relate to the physical variables by $x_{\text{scaled}} = E^{-1} x$ and $y_{\text{scaled}} = D^{-1} y$.  
  Upon convergence, our post-processor performs an exact unscaling:  
  $$x^* = E \cdot x_{\text{scaled}}^*, \quad y^* = D \cdot y_{\text{scaled}}^*$$  
  This guarantees that all reported flow rates (barrels/day) and shadow prices (\$/bbl) represent the exact physical units of the plant."*

---

# CATEGORY E: Business Case, ROI & Economic Impact

### Q18. What is the concrete financial ROI for an Indian PSU like MRPL or IOCL?
* **What the judge is testing:** Can this project justify funding, adoption, and deployment?
* **Winning Answer:**  
  *"The financial return operates on two levels:  
  1. **Direct Software License Savings:** Gurobi and CPLEX enterprise licenses cost ₹15 to ₹40 Lakhs per multi-core server annually. Replacing 10 commercial solver installations across Indian refineries saves **₹3 to ₹5 Crores annually** in pure software licensing foreign exchange.  
  2. **Refining Margin Optimization:** A 15 MMTPA refinery like MRPL processes ~300,000 barrels per day. Because our GPU solver runs in 1.5 seconds instead of 40 minutes, schedulers can perform **real-time intra-day re-optimization** as crude spot prices fluctuate. Capturing just **\$0.10 to \$0.15 per barrel** in margin optimization yields **₹80 to ₹120+ Crores annually** per refinery in operational gain."*

---

### Q19. Refineries already have commercial planning tools like Aspen PIMS or Haverly GRTMPS. Why would they replace them with yours?
* **What the judge is testing:** Commercial ecosystem awareness.
* **Winning Answer:**  
  *"We do not ask refineries to discard their entire planning workflow. Aspen PIMS and Haverly GRTMPS are front-end modelers—under the hood, they generate standard **MPS linear programming files** and call a third-party solver like Gurobi, CPLEX, or Xpress.  
  Our solver features a **native .MPS parser**. It can serve as a drop-in **replacement solver engine** behind existing modeling front-ends, immediately cutting foreign license fees and providing GPU acceleration without disrupting user workflows."*

---

# CATEGORY F: Comparison Against Existing Commercial Giants

### Q20. Gurobi and CPLEX have 30+ years of R&D and hundreds of developers. How can a student hackathon team compete?
* **What the judge is testing:** Humility, realism, and differentiation.
* **Winning Answer:**  
  *"We are not trying to replicate 30 years of legacy CPU Simplex code. In fact, Gurobi and CPLEX's massive legacy C++ codebase is their biggest disadvantage—it is deeply tied to sequential CPU architecture and cannot easily transition to GPUs.  
  We took advantage of a **paradigm shift** in mathematical optimization: first-order PDHG methods (pioneered by Chambolle-Pock and Google Research's PDLP in 2021). By building from scratch on modern CUDA GPU hardware with sparse representations, a nimble, focused architecture can outperform legacy solvers on large-scale sparse linear programs."*

---

### Q21. Can your solver handle problems with 1 Million variables?
* **What the judge is testing:** Scalability testing limits.
* **Winning Answer:**  
  *"Yes. In our synthetic stress benchmarks (`test_validate.py`), we evaluated memory scaling up to 25,000 variables and calculated theoretical VRAM limits.  
  Because our memory scales with non-zeros $O(\text{NNZ})$ using CSR matrices, a 1-million variable problem with 0.1% density has ~1 million non-zeros, requiring **under 25 Megabytes of VRAM**. An 8GB GPU has enough capacity for **364 million non-zeros**. Memory is not the barrier; GPU parallel scaling is."*

---

# CATEGORY G: National Security, Sovereignty & Atmanirbhar Bharat

### Q22. How does this project support the 'Atmanirbhar Bharat' (Self-Reliant India) initiative?
* **What the judge is testing:** Alignment with MoPNG and Government of India mandates.
* **Winning Answer:**  
  *"Mathematical optimization is the invisible brain behind critical infrastructure—not just oil refineries, but the National Power Grid (POSOCO), Indian Railways freight scheduling, and Defense logistics.  
  Currently, India has **zero sovereign commercial mathematical optimization solvers**; we are 100% dependent on proprietary US and European binaries. If technological sanctions or export controls are imposed, our energy distribution planning could be paralyzed.  
  PDHG-GPU provides India with a **100% indigenous, sovereign solver core** that runs air-gapped on national infrastructure."*

---

# CATEGORY H: Deployment, Scalability & Long-Term Maintenance

### Q23. What is your roadmap for taking this from a hackathon prototype to production refinery deployment?
* **What the judge is testing:** Realistic engineering maturity.
* **Winning Answer:**  
  *"We have a 3-phase deployment roadmap:  
  - **Phase 1 (Current Prototype):** Validated on Netlib MPS benchmarks, IOCL 8-crude digital twin, and live web SCADA UI.  
  - **Phase 2 (Pilot Integration - 3 to 6 Months):** Containerize into a microservice (Docker/REST API) and run parallel shadow testing alongside existing commercial solvers at an IOCL or MRPL planning department, comparing execution speed and margin agreement on historic daily MPS runs.  
  - **Phase 3 (Enterprise Hardening - 6 to 12 Months):** Expand native support for Python Pyomo and Julia JuMP interfaces, implement multi-GPU scaling via NCCL, and release under a sovereign open-source framework supported by MoPNG and CDAC."*

---

### Q24. How do you plan to handle solver bugs or edge cases in production?
* **What the judge is testing:** Software engineering reliability.
* **Winning Answer:**  
  *"Our codebase is architected with strict defensive engineering:  
  1. **Automated Validation Suite:** 7 automated test suites verifying KKT stationarity, primal-dual feasibility, and objective alignment against SciPy reference baselines.  
  2. **Safe Fallback Mechanism:** If the GPU encounters memory exhaustion or fails to reach target tolerance within maximum iterations, the system automatically triggers an automated fallback to multi-threaded CPU solving.  
  3. **Reproducibility:** Every solve run logs its complete convergence trajectory, residual history, and hardware telemetry to enable deterministic debugging."*

---

## ⚡ 10-Second Emergency Response Strategy
If a judge asks an extremely unexpected or hostile question:
1. **Never guess or make up math:** Acknowledge the question with technical poise.
2. **Re-anchor to the core architecture:**  
   *"That is an excellent point. In our first-order PDHG architecture, that specific behavior is governed by our Ruiz preconditioning and step-size balancing..."*
3. **Point to your live prototype:**  
   *"We actually have that scenario modeled right here in our live dashboard—allow us to run that benchmark for you right now."*
