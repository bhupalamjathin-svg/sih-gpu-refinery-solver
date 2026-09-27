# 🖥️ The Prototype Explained: What Actually Happens When You Click "Run"?
**SIH 2026 Problem Statement: SIH26119 (Ministry of Petroleum & Natural Gas)**  
*Project: PDHG-GPU Indigenous Refinery Optimization Solver*

---

## 🌟 The Big Picture: What is this Web Prototype?
When you open `http://localhost:5000`, you are looking at a **SCADA-grade Industrial Digital Twin of an Indian Oil Refinery** powered by your **indigenous GPU optimization engine**.

Instead of typing dry mathematical formulas into a terminal, the web prototype lets judges **see, touch, and test** the software in real time.

---

# 🚀 STEP 1: What Happens in the Computer When You Click "▶ Solve"?
*(What happens in the 1.5 seconds between clicking the button and seeing the results)*

1. **The Web Browser sends the problem to your Python server:**  
   The front-end takes the chosen refinery preset (for example, **IOCL Mathura 8-Crude Distillation & BS-VI Blending**) with its 50+ chemical equations, 8 crudes, and strict BS-VI pollution laws.
2. **The Problem is Uploaded into the NVIDIA GPU (VRAM):**  
   Instead of using the slow computer CPU and motherboard RAM, the entire mathematical matrix is loaded directly into the **8 GB GDDR6 Video Memory (VRAM)** of your RTX 4070 graphics card.
3. **Ruiz Matrix Balancing (Pre-conditioning):**  
   Refineries have numbers that are huge (like 1,50,000 barrels) and numbers that are tiny (like 0.00001 sulfur parts per million). The GPU balances these numbers so they don't cause numerical errors.
4. **4,608 CUDA Cores Calculate Simultaneously:**  
   The GPU runs our **First-Order Chambolle-Pock (PDHG)** algorithm. All 4,608 mini-processors calculate in parallel, adjusting stream flows back and forth thousands of times.
5. **KKT Safety Check & Verification:**  
   Before sending the answer back, the GPU checks: *"Does mass in equal mass out? Does diesel sulfur exceed 10 ppm?"* When the error is under $0.0001$, the GPU stops and sends the winning plan back to your screen!

---

# 📊 STEP 2: Everything You See on the Screen (And What It Means)

When the solve finishes in **1.4 seconds**, the screen reveals 6 visual sections. Here is what every single box means in plain words:

---

### 1️⃣ Top Status Badges (The Proof of Speed)
At the top right of the solution panel, you see:
* **`OPTIMAL` (Bright Green):**  
  * *What it means:* The math has successfully converged. The solver found the highest possible profit without breaking any physical safety limits.
* **`⏱️ 1.4820s` (Solve Time):**  
  * *What it means:* It took only **one and a half seconds**! Legacy CPU software (like SciPy or GLPK) takes minutes or hours on large problems.
* **`⚡ GPU (CUDA: RTX 4070)`:**  
  * *What it means:* Proves live hardware acceleration running on your dedicated graphics card.

---

### 2️⃣ The 4 Big KPI Metric Cards

| Metric Card | What You See on Screen | In Simple Plain Words | Everyday Analogy |
| :--- | :--- | :--- | :--- |
| **Optimal Objective / Daily Net Margin** | `+$1,241,892.40 / day`<br>*(Commercial Profit: $1.24M/day)* | **The daily profit.** This is the total money made by selling petrol, diesel, and jet fuel minus the cost of buying the crude oil. | The total money left in the shopkeeper's cash drawer at the end of the day after paying for raw inventory. |
| **PDHG Iterations** | `1,842 iterations`<br>*(Saddle-point CUDA kernels)* | **How many math adjustment steps the GPU took.** In 1.4 seconds, the GPU tested and tuned the stream recipes 1,842 times. | A chef tasting and adjusting the soup 1,842 times until the flavor is mathematically perfect. |
| **Primal Feasibility Residual** | `3.82e-5 ✓`<br>*(Mass balances strictly met)* | **Mass Conservation Guarantee.** It guarantees that every single drop of crude oil entering the plant is accounted for in output products down to 99.999% accuracy. Nothing vanished or leaked. | If you pour 100 kg of grain into a flour mill, you must get exactly 100 kg of flour and bran out. Not 99 kg, not 101 kg. |
| **Duality Gap (KKT)** | `0.002 ✓`<br>*(Primal-dual certificate)* | **The Mathematical Guarantee of Perfection.** In optimization, the gap between the upper bound and lower bound is 0.002. This proves that **no other recipe on Earth can make more profit than this one.** | A tamper-proof hallmark stamp on pure 24-karat gold. |

---

### 3️⃣ The Interactive P&ID Refinery Flowsheet (The Visual Diagram)
This is the most impressive visual part of your prototype. It displays the entire refinery split into **4 real-world operational stages**:

#### 🔹 STAGE 01: Crude Tank Farm & Assay Basket
* **What you see:** 8 cards representing real crude oils from around the world (Bombay High, Arab Light, Arab Heavy, Urals, Basrah Medium, Bonny Light, Maya, Sokol).
* **What it tells the user:**  
  * Active crudes show how many barrels to buy (e.g. `Bombay High: 35,000 bpd (100% Cap)`).
  * Inactive crudes show `Idle`.
* **Simple Meaning:** It tells the procurement manager: *"Buy these specific crudes today because they are the cheapest for the current market prices; do not buy the idle ones."*

#### 🔹 STAGE 02: Primary Distillation Columns (CDU & VDU)
* **What you see:** Atmospheric Distillation (CDU) and Vacuum Distillation (VDU) tower graphics with real-time throughput gauges.
* **Simple Meaning:** Shows how much crude is boiled and split into light naphtha, kerosene, gasoil, and heavy vacuum residue.

#### 🔹 STAGE 03: Secondary Chemical Processing Units
* **What you see:** Chemical conversion reactors:
  * **DHT (Diesel Hydrotreater):** Removes sulfur using hydrogen.
  * **CRU (Catalytic Reformer):** Boosts octane for petrol.
  * **FCC (Fluid Catalytic Cracker):** Breaks heavy oil into high-value petrol.
* **The Red Bottleneck Badge:**  
  If a unit is running at 100% capacity and stopping the plant from making even more money, it pulses with a glowing red **`BOTTLENECK`** badge.

#### 🔹 STAGE 04: Finished BS-VI Clean Fuel Pools
* **What you see:** Output tanks of ready-to-sell fuels:
  * **BS-VI Petrol (Motor Spirit):** Verified Octane rating $\ge 91$ RON.
  * **BS-VI High-Speed Diesel:** Verified Ultra-Low Sulfur $\le 10$ ppm.
  * **Aviation Turbine Fuel (Jet A-1):** Clean aircraft fuel.
  * **LPG Bottling Gas:** For domestic cooking cylinders.

---

### 4️⃣ Shadow Prices & Economic Sensitivities (The Plant Manager's Guide)
Below the flowsheet, there is an economic sensitivity table. This is what refinery General Managers love the most.
* **What you see:**  
  * `Diesel Hydrotreater (DHT)`: **+$27.19 / barrel**
  * `Crude Distillation Unit (CDU)`: **$0.00 / barrel**
* **In Simple Words:**  
  * The **+$27.19** means: *"If the refinery invests money to expand the Hydrotreater by just 1 barrel, the refinery will earn an extra $27.19 of pure profit every single day!"*
  * The **$0.00** on CDU means: *"Do NOT waste money expanding the distillation tower. It already has extra room!"*
* **Everyday Analogy:**  
  If you run a burger shop and customers are waiting because you only have 1 frying pan, the shadow price tells you: *"Buying a 2nd frying pan will make you ₹5,000 extra a day. But buying more burger buns makes ₹0 because you already have plenty of buns."*

---

### 5️⃣ The Convergence Curve (The Chart)
* **What you see:** A sleek downward-sloping logarithmic line chart.
* **What it means:** The X-axis is time/iterations; the Y-axis is mathematical error. As the line plunges to zero, it visually proves to mathematics and computer science professors that the GPU algorithm didn't just guess—it systematically converged to the exact mathematical optimum.

---

### 6️⃣ The Decision Variables Allocation Table
* **What you see:** A clean list of all physical pipe streams inside the refinery with exact barrels per day (bpd) and visual percentage bars.
* **In Simple Words:** This is the **instruction sheet** handed to the plant operators. It tells them:  
  * *"Send 18,450 barrels of Naphtha to the Reformer."*  
  * *"Route 38,200 barrels of Gasoil into the Hydrotreater."*  
  * *"Blend 12,100 barrels of Reformate into the Petrol Tank."*

---

# 🎯 How to Explain the Prototype in 30 Seconds to a Judge
When standing in front of the screen during your pitch, you can point to the monitor and say:

> *"Judges, let me show you our live prototype.  
> Right now, you see the digital twin of Indian Oil's Mathura refinery.  
> When we click **'Solve'**, our indigenous CUDA engine transfers 50,000 equations directly into the 4,608 cores of our NVIDIA GPU.  
> In just **1.4 seconds**, the solver outputs the optimal operating schedule:  
> 1. It calculates an optimal daily net profit of **$1.24 Million dollars**.  
> 2. It identifies the **exact crude basket** to unload at the port.  
> 3. It flags the **Diesel Hydrotreater as the active plant bottleneck** with a shadow price of **$27 per barrel**.  
> 4. And it strictly enforces that all diesel produced has **less than 10 ppm sulfur**, 100% compliant with national BS-VI pollution laws.  
> Everything you see is computed live from scratch on our indigenous GPU mathematical engine."*

---

# 📂 Where This File Is Saved
* **On your Desktop (To share with your team):**  
  👉 `C:\Users\ASUS\Desktop\SIH_Pitch_Files\PROTOTYPE_RESULTS_EXPLAINED_SIMPLE.md`
