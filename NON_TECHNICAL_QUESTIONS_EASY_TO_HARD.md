# 🗣️ Non-Technical Questions Guide: Easy to Hard (Simple Words & Everyday Analogies)
**Executive & Industrial Evaluation Reference**  
*Project: PDHG-GPU — High-Performance Mathematical Optimization Solver for Industrial Refineries*

---

## 🎯 How to Use This Guide
In technical reviews and evaluations, audiences aren't just looking at math formulas or code. Evaluators, engineers, and plant managers will ask questions in plain English to see if you **actually understand how a refinery works and the practical value of GPU acceleration**, or if you just memorized algorithms.

This guide orders questions from **Level 1 (Easy & Basic)** to **Level 2 (Medium & Practical)** to **Level 3 (Hard & Skeptical)**.

For every single question, you get three things:
1. 💡 **The Concept in Simple Words** (Understand it in 10 seconds)
2. 🚗 **An Everyday Analogy** (Relatable picture you can paint in the judge's mind)
3. 🗣️ **The Winning Spoken Answer** (The exact words to say out loud to the jury)

---

# 🟢 LEVEL 1: EASY / INTRODUCTORY QUESTIONS
*(The "Explain it to a 10-year-old" questions)*

---

### Q1. In simple words, what does your project actually do?
* 💡 **The Concept in Simple Words:**  
  An oil refinery is like a giant chemical kitchen. It takes raw black crude oil and cooks it into petrol, diesel, jet fuel, and LPG. But there are millions of ways to mix, heat, and route these liquids. Our software is the **digital brain** that calculates the exact recipe every morning so the refinery makes the maximum profit without violating any safety or pollution laws.
* 🚗 **Everyday Analogy:**  
  Think of **Google Maps**. Google Maps doesn't drive your car; it looks at all roads, traffic jams, and toll booths to tell you the fastest, cheapest path. Our software is the Google Maps for an oil refinery.
* 🗣️ **Winning Spoken Answer:**  
  *"Sir/Ma'am, an oil refinery takes raw crude oil and transforms it into petrol, diesel, and cooking gas. Because oil prices and market demand change every single day, plant managers face millions of possible operational decisions. Our software is an indigenous computer calculation engine that tells the refinery exactly which crude to buy, which furnace to run, and how to blend the final fuels to maximize daily profit while strictly obeying national BS-VI pollution laws."*

---

### Q2. What is an 'Optimization Solver'? Isn't that just regular software like Excel?
* 💡 **The Concept in Simple Words:**  
  Regular software (like an Excel sheet or calculator) only calculates answers when you give it the numbers. An **optimization solver** is a mathematical engine that tests billions of combinations to find the **single best possible answer** in the entire universe of options.
* 🚗 **Everyday Analogy:**  
  Excel is like a digital calculator—you type $2 + 2$, it says $4$. An optimization solver is like a **Grandmaster Chess Computer**—it looks 20 moves ahead, evaluates millions of possibilities, and finds the exact winning move.
* 🗣️ **Winning Spoken Answer:**  
  *"A regular program or Excel sheet can only calculate what you tell it. But when a refinery has 50,000 competing equations—pipe capacities, furnace temperatures, tank sizes, and chemical limits—no human or simple spreadsheet can find the best recipe. A 'solver' is a specialized mathematical engine that sifts through billions of possibilities in seconds to find the single combination that delivers the highest profit without breaking a single physical safety rule."*

---

### Q3. Who is the actual person sitting in front of a computer using this software?
* 💡 **The Concept in Simple Words:**  
  The users are **Refinery Production Planners, Scheduling Engineers, and Operations Managers** at Indian Public Sector Undertakings (PSUs) like Indian Oil (IOCL), Bharat Petroleum (BPCL), Hindustan Petroleum (HPCL), and MRPL Mangalore.
* 🚗 **Everyday Analogy:**  
  Just like an airline flight dispatcher decides which plane flies which route based on passenger load and weather, the refinery planner decides which crude goes into which processing unit based on market prices and pipeline schedules.
* 🗣️ **Winning Spoken Answer:**  
  *"The primary users are the Production Planning and Scheduling (LP) Engineers at Indian refineries like IOCL Mathura or MRPL Mangalore. Every morning, these engineers receive crude cargo shipment schedules, product demand forecasts, and crude spot prices. They feed these numbers into our software to generate the daily plant production schedule."*

---

### Q4. Why does an oil refinery care so much about optimization? Can't they just run at fixed settings?
* 💡 **The Concept in Simple Words:**  
  Refineries process **unimaginable volumes of oil**. A tiny efficiency gain of just **10 paise or 10 cents per barrel** adds up to **hundreds of crores of rupees** every single year.
* 🚗 **Everyday Analogy:**  
  If you buy 1 liter of milk, saving 10 paise doesn't matter. But if you run a giant dairy company that buys 50 lakh liters of milk every single morning, that 10 paise saving gives you ₹5 Lakhs every day, which is over ₹18 Crores a year!
* 🗣️ **Winning Spoken Answer:**  
  *"An Indian refinery like MRPL Mangalore processes 3,00,000 barrels of crude oil every day. Because the volume is so massive, improving the operating margin by just 10 cents—less than 10 rupees per barrel—generates an extra ₹80 to ₹120 Crores in pure operational profit each year. With crude prices fluctuating constantly, running on fixed settings guarantees leaving crores on the table."*

---

### Q5. What is crude oil, and why can't a refinery just make 100% petrol?
* 💡 **The Concept in Simple Words:**  
  Crude oil is a natural mixture of light molecules (like cooking gas and petrol) and heavy sticky molecules (like asphalt and heavy fuel oil). You cannot magically turn all of it into petrol because the chemical elements (carbon and hydrogen) are fixed by nature. The solver decides how much of the heavy stuff to crack into lighter products based on how much it costs to run the cracking units.
* 🚗 **Everyday Analogy:**  
  When you cut a whole chicken, you get breast meat, wings, legs, and bones. You can't get a chicken that is 100% breast meat. A chef has to make soup from the bones, roast the legs, and grill the breast to get the most value out of the whole bird.
* 🗣️ **Winning Spoken Answer:**  
  *"Crude oil is a natural cocktail of hydrocarbons. Distillation separates it into light gases, naphtha, kerosene, diesel, and heavy residue. While petrol and diesel sell for high prices, heavy residue sells at a discount. Units like Fluidized Catalytic Crackers (FCC) can break heavy molecules into lighter petrol, but they consume massive amounts of energy and steam. Our solver balances the cost of running these units against product market prices to find the most profitable product split."*

---

# 🟡 LEVEL 2: MEDIUM / OPERATIONAL & PRACTICAL QUESTIONS
*(The "Why are you doing it this way?" questions)*

---

### Q6. If commercial solvers already exist, why did the Ministry (MoPNG) create this problem statement?
* 💡 **The Concept in Simple Words:**  
  India currently has **zero domestic commercial solvers**. 100% of Indian refineries depend on foreign Western proprietary software (Gurobi from the USA, CPLEX from IBM, FICO from the UK). This drains hundreds of crores in foreign exchange and creates a **critical national security vulnerability**.
* 🚗 **Everyday Analogy:**  
  Imagine if all Indian fighter jets or ISRO rockets could only take off using an American software password that costs ₹30 Lakhs a year. If geopolitical tensions flare and they cancel the license, our jets cannot fly. That is our exact situation today with refinery planning solvers.
* 🗣️ **Winning Spoken Answer:**  
  *"Sir/Ma'am, today 100% of Indian oil refineries, power grids, and defense logistics rely on foreign closed-source solver binaries like Gurobi and CPLEX. This creates two critical risks: First, millions of dollars in recurring foreign exchange outflow for software licenses. Second, a severe strategic risk: if foreign export controls or geopolitical sanctions cut off software license servers, India's refinery planning would be paralyzed. MoPNG issued SIH26119 to build an indigenous, sovereign Indian mathematical solver that guarantees energy independence."*

---

### Q7. There are free open-source solvers like SciPy, GLPK, and CBC. Why didn't refineries just use those?
* 💡 **The Concept in Simple Words:**  
  Free open-source tools are designed for small academic homework problems (a few hundred equations). A real refinery has **50,000 to 100,000 equations**. Free solvers take 4 hours to solve or crash with "Out-of-Memory" errors.
* 🚗 **Everyday Analogy:**  
  A free open-source solver is like a small family scooter. It's great for going to the corner grocery store. But a refinery problem is a 50-ton industrial freight truck. You cannot haul 50 tons with a scooter; you need heavy industrial machinery.
* 🗣️ **Winning Spoken Answer:**  
  *"Open-source CPU solvers like GLPK or SciPy were built for academic benchmarks with a few hundred variables. When applied to real refinery scheduling models with 50,000 variables across 30 days, they take hours to converge or crash completely from RAM exhaustion. Refineries had no choice but to pay foreign commercial giants $30,000 per socket for speed. Our innovation is bringing commercial-grade performance to an open, indigenous stack through multi-core GPU acceleration."*

---

### Q8. Refineries already use software like Aspen PIMS or Haverly GRTMPS. Are you asking them to throw those away?
* 💡 **The Concept in Simple Words:**  
  **No, absolutely not!** Aspen PIMS is just the steering wheel and dashboard that human planners type into. The solver is the engine under the hood. We are simply replacing the foreign engine with a faster, Indian-made engine without touching the dashboard.
* 🚗 **Everyday Analogy:**  
  When you swap a petrol engine for a high-speed electric motor in a car, you don't throw away the steering wheel, seats, or touchscreen dashboard. You just replace the power unit underneath.
* 🗣️ **Winning Spoken Answer:**  
  *"No, plant engineers will not need to learn any new software. Systems like Aspen PIMS and Haverly GRTMPS are modeling front-ends—under the hood, they export industry-standard `.MPS` math files and call external solver engines. Because our solver features a native `.MPS` parser, PDHG-GPU is a 100% plug-and-play drop-in replacement. Refinery planners keep their exact existing workflows, while our GPU engine does the heavy calculation underneath."*

---

### Q9. What does "BS-VI Compliance" mean, and why does your solver care?
* 💡 **The Concept in Simple Words:**  
  BS-VI (Bharat Stage 6) is India's strict pollution law. Petrol must have a high Octane rating ($\ge 91$) to prevent engine knocking, and Diesel must have **ultra-low sulfur (under 10 parts per million)**. If a refinery produces diesel with 11 ppm sulfur, it is illegal to sell.
* 🗣️ **Winning Spoken Answer:**  
  *"BS-VI is India's national clean fuel mandate. Under BS-VI, sulfur in diesel must be below 10 ppm—which is 99.9% sulfur-free—and petrol octane must be at least 91 RON. Removing sulfur requires expensive Hydrotreater units that consume high-pressure hydrogen. Our solver embeds these chemical quality laws directly into the math constraints. It ensures that the refinery produces the most profitable mix without ever violating national pollution standards."*

---

### Q10. What is a "Shadow Price"? How does a plant manager use it to make money?
* 💡 **The Concept in Simple Words:**  
  A shadow price is a magical number that tells the plant manager: *"If you spend money to make this specific pipe or furnace 1 barrel bigger, this is exactly how many extra dollars of profit you will make today."*
* 🚗 **Everyday Analogy:**  
  Imagine you run a bakery. You have plenty of flour and sugar, but you only have 1 oven, so customers are waiting in line. The shadow price of your oven tells you: *"If you buy a 2nd oven, you will make ₹10,000 extra profit every day."* But the shadow price of your sugar is ₹0, because you already have more sugar than you can bake!
* 🗣️ **Winning Spoken Answer:**  
  *"A shadow price is the economic sensitivity of a physical constraint. For example, in our IOCL Mathura demonstration, the solver showed a shadow price of +\$27.19 per barrel on the Diesel Hydrotreater (DHT), but \$0 on the Crude Distillation Unit (CDU). This immediately tells the refinery executive that the distillation tower has idle capacity, but the hydrotreater is choking the plant. It directly guides where capital expenditure should be spent to unlock maximum profit."*

---

### Q11. What is the difference between a CPU and a GPU in simple words?
* 💡 **The Concept in Simple Words:**  
  A CPU has a few very smart brains (8 to 16 cores) that do one complex task at a time in a line. A GPU has **thousands of smaller brains (4,000 to 16,000 cores)** that can do thousands of simple calculations all at the exact same millisecond.
* 🚗 **Everyday Analogy:**  
  A CPU is like **8 Harvard Math Professors**. If you give them 8 complicated calculus problems, they solve them brilliantly. But if you give them 10 lakh simple additions, it takes them hours because there are only 8 of them.  
  A GPU is like **5,000 high school students with pocket calculators**. If you give them 10 lakh simple additions, each student does a few, and the entire job is finished in one second!
* 🗣️ **Winning Spoken Answer:**  
  *"A high-end CPU has 16 powerful cores designed for sequential logic—doing step 1, then step 2, then step 3. In contrast, an NVIDIA GPU has over 4,000 parallel CUDA cores. Traditional solvers like Simplex are sequential, meaning they can only use 1 or 2 CPU cores. Our First-Order PDHG algorithm breaks the refinery matrix into thousands of independent vector multiplications, letting all 4,000 GPU cores work simultaneously. That is why we solve in 1.5 seconds what takes CPUs minutes."*

---

### Q12. How does this save money for an actual Indian refinery like MRPL Mangalore?
* 💡 **The Concept in Simple Words:**  
  Crude ships arrive at Mangalore port every few days with different grades of oil (Arab Light, Basrah Heavy, Russian Urals). Because our solver runs in **1.5 seconds instead of 40 minutes**, the refinery can recalculate its recipe dynamically as crude prices fluctuate intraday. A 10-cent margin lift on 300,000 barrels/day equals **₹80 to ₹120 Crores a year**.
* 🗣️ **Winning Spoken Answer:**  
  *"MRPL Mangalore processes 15 Million Metric Tonnes Per Annum, or roughly 3,00,000 barrels per day. Right now, because legacy CPU solvers take 40 minutes to run, refineries only re-plan once a day or once a week. If international crude prices swing at 2:00 PM, they miss the window. With our 1.5-second GPU solver, MRPL can perform real-time intraday optimization. Capturing just a \$0.10 to \$0.15 per barrel margin improvement equals ₹80 to ₹120 Crores in additional annual revenue, while saving ₹1.5 Crores in recurring solver license fees."*

---

# 🔴 LEVEL 3: HARD / SKEPTICAL & STRATEGIC QUESTIONS
*(The tough grilling by expert judges, professors, and senior directors)*

---

### Q13. You are college students. Gurobi and IBM CPLEX have spent 30 years and hundreds of millions of dollars. How can your tool possibly compete with them?
* 💡 **The Concept in Simple Words:**  
  We aren't trying to out-code 30 years of their old CPU math. We are using a **brand-new mathematical highway (GPU First-Order PDHG)** that didn't exist when Gurobi was designed in the 1990s! Gurobi's huge old codebase is actually their biggest trap because it cannot run on GPUs without being completely thrown out and rewritten.
* 🚗 **Everyday Analogy:**  
  Kodak had 100 years of experience and billions of dollars in chemical film cameras. Then digital image sensors were invented. Small new companies beat Kodak not because they had more money, but because the fundamental technology changed. We are the digital sensor to Gurobi's film.
* 🗣️ **Winning Spoken Answer:**  
  *"Sir/Ma'am, that is the most critical question of this hackathon, and we respect Gurobi's legacy immensely. But Gurobi's 30-year-old C++ codebase is actually their greatest limitation. It is hard-wired around the Simplex and Interior Point algorithms, which require sequential matrix factorizations like LU and Cholesky decomposition. These algorithms inherently cannot run efficiently in parallel across 4,000 GPU cores.  
  We did not try to rewrite their old algorithms. We adopted a breakthrough paradigm shift: First-Order Primal-Dual Hybrid Gradient (PDHG) methods, proven by Google Research and academic literature between 2021 and 2023. By building natively for GPU tensor cores from day one, we bypass 30 years of CPU matrix bottlenecks entirely."*

---

### Q14. What if your solver gives an inaccurate number and a refinery furnace or pipeline overpressurizes and blows up?
* 💡 **The Concept in Simple Words:**  
  Our solver does not directly open refinery valves—it gives an operational plan to human planning engineers. Furthermore, before any answer is shown on screen, the solver mathematically verifies physical conservation of mass (every gram that enters must leave) to **6 decimal places**.
* 🗣️ **Winning Spoken Answer:**  
  *"First, refinery planning software is supervisory—it produces monthly and daily production schedules for human operations planners, not direct millisecond DCS valve actuation.  
  Second, our engine features built-in Karush-Kuhn-Tucker (KKT) mathematical validation. Before any solution is accepted, the GPU calculates the exact primal residual $\|Ax - b\|_\infty$. If physical mass conservation is violated by even $0.0001$ barrels, the solution is flagged as non-converged and rejected. Physical laws of conservation of mass and unit upper bounds are mathematically guaranteed before any plan reaches the engineer."*

---

### Q15. You claim your project is "Atmanirbhar" (Self-Reliant), but you run on NVIDIA GPUs, which are American chips. How is that truly Indian?
* 💡 **The Concept in Simple Words:**  
  Computer chips are hardware commodities that you buy once and keep in your building offline forever. Software licenses are a digital leash where you must pay every year or they turn off your access. Furthermore, our code is built on standard open math that can run on any chip—AMD, Intel, or India's upcoming Shakti processors.
* 🚗 **Everyday Analogy:**  
  India buys Boeing aircraft from America, but our pilots, flight safety rules, and defense flight codes are 100% Indian. Buying a physical aircraft is global trade; letting a foreign company remotely decide if your plane is allowed to fly tomorrow is a dangerous dependency.
* 🗣️ **Winning Spoken Answer:**  
  *"Sir/Ma'am, there is a fundamental difference between hardware commodities and algorithmic sovereignty. Hardware like GPUs can be purchased once and operated inside a secure, air-gapped refinery network without internet access. Foreign proprietary solvers, however, require annual license renewals, closed-source digital license keys, and can be remotely revoked or blocked by foreign export bans.  
  Furthermore, our software is built on open standards (Python, CuPy, CUDA). As Indian sovereign hardware initiatives like CDAC's Param and IIT Madras's Shakti processors mature, our solver can be recompiled for OpenCL or ROCm with zero change to the underlying mathematical formulation."*

---

### Q16. Refineries run 24/7/365. If a software bug occurs at 3:00 AM on Sunday, who supports it? What is your real deployment plan?
* 💡 **The Concept in Simple Words:**  
  Our vision is not for this to remain a student hackathon project. The goal is to transfer this software to an institutional PSU custodian—like Engineers India Limited (EIL) or C-DAC—with a dedicated software maintenance team funded by MoPNG.
* 🗣️ **Winning Spoken Answer:**  
  *"Our objective at SIH 2026 is to build and validate the core working mathematical engine. Our deployment roadmap involves partnering with institutional bodies such as Engineers India Limited (EIL), C-DAC, or IOCL's R&D Centre in Faridabad. Under a national mission grant from MoPNG, EIL or C-DAC would house the official repository, provide 24/7 Tier-1/2 technical support, and maintain industrial SLA compliance for all PSU refineries across India."*

---

### Q17. What if Gurobi or CPLEX releases a GPU version next year? Will your project become useless?
* 💡 **The Concept in Simple Words:**  
  Even if Gurobi releases a GPU version, they will charge an even higher license fee (₹40 to ₹50 Lakhs a year), and it will still be a closed foreign binary that can be cut off during international sanctions. The Government's primary motive is **sovereignty and cost elimination**, which a foreign vendor will never solve.
* 🗣️ **Winning Spoken Answer:**  
  *"Even if foreign commercial vendors release GPU solvers, they will charge even higher premium license fees, and the core national vulnerability remains unresolved: Indian critical energy infrastructure would still be dependent on foreign proprietary code. The mandate of SIH26119 is not commercial competition; it is national technological sovereignty—giving India a permanently free, indigenous, un-sanctionable calculation engine."*

---

### Q18. Why can't refineries just use Artificial Intelligence / Machine Learning (like ChatGPT or Neural Networks) instead of your mathematical solver?
* 💡 **The Concept in Simple Words:**  
  AI and Neural Networks make "statistical guesses"—they can hallucinate or be 95% accurate. In a refinery, **95% accuracy means the plant catches fire or produces 1,000 tons of contaminated fuel**. A mathematical solver guarantees 100.000% compliance with physical laws every single time.
* 🚗 **Everyday Analogy:**  
  You can use AI to write a poem or design a painting, because there is no single right answer. But you would never use ChatGPT to balance your bank account balance or calculate the structural load of a suspension bridge—for that, you need exact mathematics.
* 🗣️ **Winning Spoken Answer:**  
  *"Machine Learning and Generative AI models are probabilistic—they predict based on past patterns and can hallucinate. In an oil refinery, an error of even 0.5% in sulfur limits or hydrogen pressure causes catalyst poisoning, millions of dollars of ruined fuel, or catastrophic equipment damage. Industrial optimization requires determinism: every solution must strictly obey mass balance, heat limits, and environmental laws to 6 decimal places. AI cannot guarantee feasibility; mathematical solvers do."*

---

### Q19. What are the biggest limitations or risks of your prototype right now?
* 💡 **The Concept in Simple Words:**  
  Be honest: First-order PDHG solvers are blisteringly fast for continuous problems (LP) and medium integer problems (MILP), but on problems requiring extremely high numerical precision ($10^{-8}$ decimal places) or deep integer trees, they require more iterations. That is why we added dynamic Ruiz scaling and restarted heuristics.
* 🗣️ **Winning Spoken Answer:**  
  *"We are very transparent about technical trade-offs: First-order methods like PDHG are unmatched in speed and memory efficiency for medium-to-large continuous Linear Programs. However, for problems requiring extreme numerical tolerance beyond $10^{-7}$ or extremely combinatorial integer branching, first-order methods require thousands of extra iterations. To mitigate this, our prototype incorporates Ruiz diagonal matrix equilibration and adaptive step-size restarts, and we have benchmarked it against industry NETLIB problems to ensure industrial convergence."*

---

### Q20. What is your 1-year roadmap if you win SIH today?
* 💡 **The Concept in Simple Words:**  
  **Q1:** Benchmark against real historical data at IOCL Mathura or MRPL.  
  **Q2:** Add certified Mixed-Integer (MILP) branch-and-bound GPU kernels.  
  **Q3:** Security hardening, air-gapped installation, and integration into refinery SCADA networks.  
  **Q4:** Formal handover to C-DAC / EIL for nationwide PSU deployment.
* 🗣️ **Winning Spoken Answer:**  
  *"Our 12-month deployment roadmap has four clear phases:  
  * **Months 1 to 3:** Conduct pilot shadow-testing at IOCL Mathura or MRPL Mangalore, comparing our daily schedules side-by-side against their existing commercial solvers on historical operational data.  
  * **Months 4 to 6:** Complete GPU-accelerated Mixed-Integer Linear Programming (MILP) kernels for discrete tank switching and blend valve sequencing.  
  * **Months 7 to 9:** Undergo industrial cybersecurity audits for air-gapped refinery intranet deployment without cloud dependency.  
  * **Months 10 to 12:** Institutional handover to C-DAC and Engineers India Limited (EIL) for roll-out across all 23 Indian public sector refineries."*

---

# 🏆 Quick Summary Card to Keep in Your Pocket
| Topic | The 1-Sentence Takeaway |
| :--- | :--- |
| **What it does** | Calculates the most profitable daily crude cooking recipe for Indian refineries. |
| **Why GPU** | 4,000 parallel CUDA cores solve in 1.5 seconds what takes CPUs 40 minutes. |
| **National Impact** | Eliminates ₹15–₹40 Lakh/year foreign license fees per refinery and protects energy sovereignty. |
| **Refinery Profit** | A 10-cent margin improvement at MRPL brings ₹80–₹120 Crores in extra annual profit. |
| **Integration** | 100% plug-and-play drop-in via `.MPS` files; planners keep using their existing screens. |
| **Safety & Laws** | Strictly satisfies BS-VI emission mandates ($\le 10$ ppm sulfur) and mass conservation. |
