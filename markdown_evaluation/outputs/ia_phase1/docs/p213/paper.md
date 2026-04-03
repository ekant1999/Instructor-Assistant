---
title: "Collaborative Task and Path Planning for Heterogeneous Robotic Teams using Multi-Agent PPO"
paper_id: 937020923872
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/260401213v1.pdf"
generated_at: "2026-04-03T22:15:46.197871+00:00"
num_figures: 3
num_tables: 0
num_equations: 21
---

Matthias Rubio 1, Julia Richter 1, Hendrik Kolvenbach 1, and Marco Hutter 1

## Abstract

Abstract— Efficient robotic extraterrestrial exploration requires robots with diverse capabilities, ranging from scientific measurement tools to advanced locomotion. A robotic team enables the distribution of tasks over multiple specialized subsystems, each providing specific expertise to complete the mission. The central challenge lies in efficiently coordinating the team to maximize utilization and the extraction of scientific value. Classical planning algorithms scale poorly with problem size, leading to long planning cycles and high inference costs due to the combinatorial growth of possible robot-target allocations and possible trajectories. Learning-based methods are a viable alternative that move the scaling concern from runtime to training time, setting a critical step towards achieving real-time planning. In this work, we present a collaborative planning strategy based on Multi-Agent Proximal Policy Optimization (MAPPO) to coordinate a team of heterogeneous robots to solve a complex target allocation and scheduling problem. We benchmark our approach against single-objective optimal solutions obtained through exhaustive search and evaluate its ability to perform online replanning in the context of a planetary exploration scenario. Index Terms— Path Planning for Multiple Mobile Robots or Agents; Space Robotics and Automation; Reinforcement Learning

## Introduction

Unmanned surface exploration may require not only different locomotion techniques to overcome harsh terrain but also a variety of scientific equipment and specific devices for physical interaction with the environment. However, a single robot has only a limited capacity. Therefore, distributing task-specific components across a team of specialized robots allows multiple tasks to be performed in parallel, reducing overall mission time [1]. In 2021, the Perseverance rover deployed the helicopter Ingenuity on Mars, achieving the first powered flight on another planet [2]. This groundbreaking mission proved that the use of multiple agents with alternative locomotion techniques has the potential to enhance future planetary exploration missions. Similarly, Arm et al. used a team of legged robots with complementary skills to perform an Earthbased resource prospecting study [3]. The team was able of performing different tasks in a short time frame, showing that collaboration increases efficiency compared to singlerobot exploration [1]. However, in the latter example, the task allocation and task sequence were determined manually by five human operators. As this becomes more complicated for more robots and tasks, especially under the communication delays and constraints of planetary missions, manual planning needs to

1 Robotic Systems Lab (RSL), ETH Z¨
urich, Z¨
urich, Switzerland

![Figure 1](assets/figures/page_001_vec_001.png)

_Figure 1: An illustrative plan for a collaborative robot fleet with different specializations, such as flying, walking, or driving. During the mission the drone and the legged robot find new tasks and replan to minimize mission time._

be replaced by an algorithm that coordinates the team on a
global scale.

For single-robot path planning, there are many possible algorithmic approaches which S´ anchez-Ib´ a˜ nez et al. systematically categorize [4]. Graph search algorithms, such as A*, make up a well-known subgroup in addition to sampling-based methods. Richter et al. show how to use a multi-objective A* global path planning algorithm for an exploration mission on the moon [5]. However, single-robot path planning algorithms fail to address the additional complexities in multi-agent scenarios. Besides finding an efficient path, the algorithm also needs to

allocate a subset of tasks and determine a specific execution order for each robot. Since multiple robots can interact and collaborate, the algorithm additionally needs to schedule the robots appropriately to avoid potential conflicts or exploit synergies between them. In a space exploration mission, not all the information is known a priori, and new regions of interest, terrain changes, or robot failures lead to unexpected situations. Hence, a fully autonomous robot team should be able to replan and adapt on site according to the available and incoming information. Especially for exploration on another planet, this prevents unnecessary communication delays and idle times while extending the available time for scientific investigation. Due to limited computational resources, such an algorithm also has to adhere to the tight real-time constraints posed by space systems. Prior work has framed the problem in different ways, e.g., as a multi-traveling salesman problem (MTSP), and taken first steps towards learning-based solutions. Nevertheless, existing methods are limited to assigning agents to targets based on individual path costs and then scheduling them in a separate step, making it difficult to handle both aspects within a single solver. In contrast, our work introduces a fully learning-based method that unifies path planning, task allocation, and scheduling for heterogeneous multi-robot teams. The main contributions can be summarized as follows.

• A MAPPO-based reinforcement learning framework for cooperative multi-agent path planning, task allocation, and scheduling.

• Benchmark against an optimal exhaustive search baseline, demonstrating competitive performance with improved scalability.

• Validation of fast replanning in dynamic environments, highlighting applicability to space exploration missions.

• Open-source release of the learning framework.1

The remainder of this paper is structured as follows. In Section III, our method is thoroughly explained, including a formal description of the problem and the training strategy. The implementation and results on performance and replanning capabilities are presented in Section IV, and finally the limitations of the method and recommendations for future work are discussed in Section V.

## Related Work

A well-known formulation of path planning problems that includes target allocation is the MTSP, where its numerous variations are listed in [6]. Exact methods to solve the MTSP include constraint programming [7] and integer programming algorithms [8]. The problem can also be extended to require collision-free paths, such as in [9], where Ma et al. present a conflict-based min-cost-flow algorithm on a time-expanded graph, or in [10], where Turpin et al. show how to decouple the target assignment and scheduling problem to solve those

parts sequentially. In general, exact methods are able to find a globally optimal solution. However, they tend to scale poorly with the number of agents and targets and therefore result in long computation times, which can go up to hours, as stated in [6]. This issue makes it hard to perform continuous replanning on constrained computational resources, such as on a space exploration rover. The state-of-the-art methods in the literature to solve MTSP problems are metaheuristic algorithms, such as NSGA-II [11] or particle-swarm optimization techniques, e.g., ant colony optimization [12] or the artificial bee colony algorithm [13,14]. Metaheuristic algorithms are popular because they can be implemented in a computationally efficient way. However, they do not guarantee finding an optimal solution in finite time or even a valid solution at all. Since the problem still scales with the number of agents and targets, a trade-off between computation time and solution quality is inevitable. Jiang et al. address this using their multiagent planning framework, which consists of two different algorithms that exhibit the trade-offs between plan quality and computational efficiency [15]. Recent work tries to investigate the capabilities of learning-based approaches, where the scaling problem shifts from runtime to training time, enabling the efficient use of computational resources in advance and having almost constant inference times. This can be particularly interesting for space applications that require real-time computation. The standard MTSP is solved using a reinforcement learning approach in [16] and [17], where the problem is separated into two stages. The first stage is a graph neural network that learns how to allocate targets to agents, and the second stage consists of a standard single-traveling salesman problem solver that is also used to supervise the network learning process. This method has been shown to outperform metaheuristic methods in solution quality from small-scale problems up to tens of agents and hundreds of cities. However, to the best of our knowledge, there are no full learningbased approaches trying to extend the MTSP to a case with collaborative tasks, which would include appropriate scheduling of the robots.

To include the full range of subproblems (target allocation, scheduling, and replanning), the problem can be framed within the context of a collaborative game-theoretic approach. In this context, rather than seeking the optimal solution in a large search space, the focus shifts to identifying a general strategy that can be learned empirically and followed consistently by the agents. This motivates the question of whether learning-based methods can be employed to learn such strategies and to what extent they approach optimality. An unsupervised approach to multi-agent path planning is presented in [18] (PRIMAL) and extended in [19] (PRI- MALc). The proposed algorithms learn a decentralized strategy to navigate towards targets while avoiding collisions. This concept was also explored in the context of socially aware navigation for multi-robot teams [20].

They demonstrated how robots can be trained to navigate efficiently in a crowded environment while ensuring safety and comfort for humans around the robots. The learning architecture consists of a spatial-temporal graph neural network that can compute an embedding expressing the human-robot and robot-robot interactions, and an underlying multi-agent proximal policy optimization (MAPPO) algorithm ( [21,22]) that learns how to compute the actions for each robot. According to [21], MAPPO has been demonstrated in different baseline environments such as the multi-agent particle-world environments (MPE), the StarCraft multi-agent challenge, Google Research Football and the Hanabi challenge. It is therefore a competitive baseline in cooperative multi-agent learning and provides a promising foundation for applying to the target allocation and scheduling problem in an exploration task.

III. M ETHOD

## Method

To learn a strategy that solves the planning problem, we construct a virtual environment containing agents and targets. Agents have the freedom to choose their actions at each step with the goal of solving all targets.

First, the positions of the targets and all agents are included in the observation of an agent as shown in Equation (2). The symbol p ∈ N 2 0 denotes an absolute position on the grid and r t q ∈ Z 2 is the relative position between an agent q and a target t. The subscripts i and k are the indices of the agents and targets, and N = |Q| and M = |T | are the number of agents or targets, respectively.

To indicate that a target is solved, its relative position is automatically set to zero by the function g(r t) in Equation (1) for all agents. The observation structure is kept agent-specific, denoted by the subscript qi, always having the position of

the current agent in the first entry of the array. Enforcing this structure allows the actor network to associate the observing agent with its position. In order to solve the targets efficiently, agents need information about the skill sets of the other agents and the skill demands of each target. Since multiple skills can be associated with an agent or a target, the observations in Equation (3) are encoded as skill sets written as S qi or S tk. In practice, skill sets are enumerated and assigned to integer values by a predetermined function f(S) : P(S) → N 0.

Finally, targets must be distinguished by their type (AND or OR type) to indicate whether collaboration is necessary. In Equation (4), the types h are encoded as 1 (AND type) or 0 (OR type).

> Equation 4 JSON: `assets/equations/equation_0002.json`
> Equation 4 image: `assets/equations/equation_0002.png`

The complete observation for an agent q i is a concatenation of the previously mentioned observations and can be written as:

Note that the observation of an agent depends on the number of agents and targets that exist in the environment. Although this design choice prevents variation in numbers during training, it eliminates the need for a separate encoding algorithm or network to handle dynamically sized observations.

In the following, the different reward terms used in the training are discussed. To help the agents navigate towards the sparsely distributed targets, an attraction reward (AR) is introduced, which is spread around a target with an increasing value towards the center. The agent receives this reward at each time step, if the target is unsolved and the agent has at least one matching skill with the target, which can be expressed as the condition P = (t ∈T U(j))∧(|S qi∩S t|) > 0. The reward function for one target is shown in Equation (6), where r t is the relative distance from agent qi to target t and C AR is a constant parameter that determines the spread of the attraction reward. The attraction reward in Equation (7) is averaged over all the targets to be solved in the environment and normalized with respect to the maximum number of steps T max.

Once a target is reached and solved, there is a fixed payout for all agents, regardless of whether they contributed to solving the target. This prevents competition among agents.

![Figure 2](assets/figures/page_004_vec_001.png)

_Figure 2: This figure illustrates the complete workflow, highlighting both the execution (green) and training (yellow) phases. The execution block details the network architectures and the placement of the replanning step. The training block shows the MAPPO update sequence. The colored arrows differentiate data flow, specifying whether it applies to all agents, a single agent, or represents aggregated data for training. Furthermore, the environment is visualized as_

> Equation 8 JSON: `assets/equations/equation_0007.json`
> Equation 8 image: `assets/equations/equation_0007.png`

The target reward (TR) function is shown in Equation (8) where j refers to the current time step. If all the targets are solved, the collected rewards sum up to 1.

> Equation 9 JSON: `assets/equations/equation_0010.json`
> Equation 9 image: `assets/equations/equation_0010.png`

( −1 if (∥r t∥2 = 0) ∧ (|S qi ∩ S t| = 0) 0 otherwise (9) To ensure efficient completion of targets, specifically minimizing the number of required steps, agents are subjected to a nominal cost per movement (SC), which can be formalized as shown in Equation (10). The action that leads to the current state is written as u(j − 1).

In addition to a minimal number of steps, agents are expected to complete the targets in a minimum time frame,

which is introduced as shown in Equation (11). The solvetime cost (TC) decreases with the number of solved goals and is normalized by the number of total targets M and the maximum number of steps T max in the episode. It follows that if the agents solve all the targets during an episode, the cost vanishes. r T C qi = |T U(j)|

Finally, the terminal bonus incentivizes agents to complete an environment further by rewarding them for solving all targets, as shown in Equation (12).

The complete reward for an agent computed at each time step is shown in Equation (13) where each reward term is weighted by a constant parameter w ∈ R, which allows the relative influence of the rewards to be adjusted in training.

Training
AR
TR
WC
SC
TC
BR

TABLE I: Activated rewards during training. AR: Attraction Reward, TR: Target Reward, WC: Wrong Target Cost, SC: Step Cost, TC: Solve Time Cost, BR: Bonus Reward

As stated in Section II-B, we use the MAPPO algorithm [21,22], due to its proven performance in cooperative multiagent settings. We follow Lowe et al. [22], using an actorcritic structure for the MAPPO networks. The actor and critic networks have a gated recurrent unit (GRU), wrapped by dense layers, as shown in Figure 2. The critic learns a joint value function in a centralized way by taking a concatenation of all the agent observations. On the other hand, the actor execution is decentralized and outputs a probability distribution over the action space. In our case, the actor learns a strategy for an agent with arbitrary skills that can be applied to any agent on the team.

The step and solve time costs are initially discouraging. This can create an exploration bottleneck early in training, where agents fail to discover rewarding behaviors and instead converge to a degenerate policy that minimizes penalty by remaining stationary. To overcome this initial difficulty, the training is divided into two parts, the so-called bootstrap and refinement. In bootstrap, agents learn how to navigate to targets based on their skills. In refinement, they learn how to solve the targets efficiently. The rewards are activated as listed in Table I. During refinement training, the attraction reward is maintained to help agents finalize their navigation strategy. Its significantly lower value, compared to other reward terms, is designed to mitigate its effect towards the end of training. In all training runs, the initial positions and the skill sets for the agents and targets, as well as the target types, are randomized. However, to ensure that an environment is solvable, the agent team is always given at least one of each required skill.

Our pipeline was implemented using the JaxMARL framework [23], which provides baseline training algorithms and template environments for multi-agent reinforcement learning. The number of environment steps, the number of minibatches, the number of parallel environments, and the total training steps were manually tuned with respect to the quality of the solution and the GPU hardware constraints. The parameters used for the different policies (with varying numbers of targets) are listed in Table II. The reward weights for the policies are shown in Table III. Depending on which training phase, the weights were set to zero according to the activation rules in Table I.

Π 5 T
Π 6 T
Π 7 T

TABLE III: Reward weights for the baseline policy.

## Results

The main results were obtained by training three agents with two different skills acting on a 32x32 map. Agents had two possible skills, implying three possible skill sets. Targets requiring both skills could be of type AND or OR. To analyze how well the method scales with the number of targets, we evaluated three different policies, Π 5 T , Π 6 T , Π 7 T , with agents solving five to seven targets. Due to the fixed observation size, as mentioned in Section III-B, the three policies had to be trained separately. During training, actions were sampled from a weighted probability distribution computed by the actor network to allow for a certain amount of exploration. For the evaluation, the action with the maximal probability was applied at each time step. The actor-critic networks, with approximately 245’000 kernel parameters, were trained on an Nvidia GeForce RTX 4090 GPU. Inference times for the trained network and the baseline were measured on a MacBook Pro with an i5 @ 2.3 GHz with 8GB of RAM.

We introduce a set of metrics to quantify the overall performance of our method. In the results, the metrics will be averaged over a series of randomly generated environments to obtain a statistical evaluation and marked with a bar M accordingly. 1) Success Rate: The success rate represents the number of solved environments K solved versus the total number of simulated environments K sims. In solved environments, all targets were solved.

2) Solve Time: T solved is the number of time steps until the agents have solved all the targets, and T max is equal to the maximum number of environment steps n ST EP S as listed in Table II. Therefore, the difference in the metric M st represents how much time is left before the environment is

TABLE IV: Performance comparison between three policies with a different number of targets, and the optimal solutions ES1 w.r.t. solve time (st) and ES2 w.r.t. the total team effort (tte). Optimal performance would be represented by a value of 1.

marked as unsolved. We use the difference to allow for a relative comparison with the baseline algorithm.

3) Total Team Effort: The total team effort is defined as the sum of all agent movements. Similarly to the solve time, we define the metric M tte as the negative counterpart, which is the sum of movements that agents have left after all targets were solved. The function r step was defined in Section III-A and evaluates to 1 for each moving action at time step j.



T max −

Although our multi-agent reinforcement learning (RL) policy is trained for a multi-objective goal, we compare its performance to optimal solutions found via exhaustive search (ES) in Table IV. This approach provides a quantitative benchmark, demonstrating how closely our policy’s performance on each metric approaches its theoretical bestcase scenario. We compute two sets of optimal solutions, optimizing ES1 with respect to M st and ES2 with respect to M tte. For each policy, we averaged the metrics over 100 different simulated environments. The success rate for all policies is greater than 90%, which shows that most environments are solved. Furthermore, the three trained policies achieve greater optimality with respect to total team effort (92%, 91%, 84%) than with respect to the solve time (86%, 81%, 73%). This indicates that the chosen reward weights led to a policy that favors team effort over solving the targets in minimal time. Furthermore, the numbers reveal a decreasing performance across all metrics as the number of targets increases, which is consistent with the problem’s growing complexity.

A notable advantage of a learning-based method is that the inference time remains constant and is independent of the problem’s initial conditions. This is because a single forward pass through the network has a time complexity of O(1). This property enables real-time operation in a resourceconstrained environment. In contrast, exact methods, such as the ES approach, exhibit an inference time that scales exponentially with the number of agents, targets, or skills.

Furthermore, the inference time of these methods varies significantly based on the initial conditions. In Figure 3, we show a comparison between the inference times for the ES approach, our policy at runtime, and the corresponding training time for a varying number of targets. The inference time for the RL policy was measured by running a simulation to its limit, which in our case is 128 steps, i.e., forward passes. For both approaches, the time was averaged over 10 simulations. The graph reveals an exponential increase of approximately 1.5 orders of magnitude for the ES solving time, whereas the RL training time grows at around 0.25 orders of magnitude. However, the RL training time is orders of magnitude beyond the ES solving time.

![Figure 3](assets/figures/page_006_vec_001.png)

_Figure 3: RL inference and training time measurements compared to the inference time of the ES approach with respect to the trained policies by number of solved targets._

Having a short and constant inference time for the network opens the possibility of performing online replanning on newly discovered targets. As described in Section III-B, the observation size is fixed and the number of targets cannot be changed for a pretrained network. Thus, we use the observation as a buffer, where new incoming targets replace those that have already been solved. For this experiment, we used Π 5 T as a baseline and an additional policy Π 5 T 5 R that was trained such that the agents had to solve the five initial targets and an additional five replanned targets in an episode. The new targets were randomly generated with different positions, skill sets and goal types and were added to the observation as soon as one of the initial targets had been solved. All training parameters and reward weights were kept the same, as was the training strategy. Both policies were simulated over 1000 environments to solve five initial and five additional targets. As listed in Table V, the results for both policies are very similar, showing that explicitly training with newly incoming targets does not improve performance. Note that the success rate M success in Table V is lower compared to the results shown in Section IV-B, because an episode was only marked

Π 5 T 5 R
84.1 %
85.73 ± 20.9
220.0 ± 81.3

TABLE V: Baseline policy Π 5 T versus a policy Π 5 T 5 R that was trained including the possibility of obtaining new targets during an episode. Simulated over 1000 random (seed=10) environments with an episode length of 128.

as successful if the agents could solve 10 targets instead of five, while the maximum duration of the episode was still 128.

## Discussion

In Section IV-B, we compared our method against two optimal solutions obtained by ES. The learned policies achieved up to 86% optimal solution quality with respect to the solve time and up to 92% with respect to the total team effort. These results demonstrate that a reinforcement learning policy can approximate near-optimal performance with significantly lower computational cost at runtime. The higher optimality with respect to total team effort compared to solve time indicates that the chosen reward weights biased the policies toward minimizing overall effort rather than completion time. In addition, performance across all metrics decreases as the number of targets increases, reflecting the growing complexity of the problem. Still, the final success rate leaves room for improvement. Training with a longer episode length could have helped to explore more edge cases and increase performance. However, GPU memory limitations imposed a trade-off between episode length (i.e., exploration horizon) and the number of environments that could be trained in parallel. As is common in reinforcement learning, reward tuning was a central challenge. When increasing the number of targets, we observed that the previously tuned parameters remained applicable only up to a certain number, beyond which re-adjustment of the weights is necessary. For example, the intensity of the attraction reward needed to be reduced when training with more targets to prevent mutual cancellation of target rewards due to excessive overlap.

When the RL method is deployed on real hardware, the inference time of a fixed-size network remains constant for an increasing number of targets. This property can prove advantageous when designing real-time embedded systems. In contrast, exact methods scale exponentially with the number of agents, targets, or skills and are highly sensitive to initial conditions. However, the findings in Figure 3 also show that the inherent complexity of the problem is not eliminated, but instead is shifted and condensed to the training phase. Training times and computational demands scale rapidly with the number of targets, agents, and skills, slowing down policy development. Moreover, the corresponding scaling rate in

Section IV-C is likely higher, since the performance decreased when additional targets were introduced (Table IV), suggesting that the training was not fully exploited.

By using the observation as a buffer and replacing solved targets with new ones, our method demonstrated its ability to perform online replanning. In real-world missions, this could be applied iteratively, rather than calculating a complete solution upfront. Plans would be generated for shorter horizons and dynamically adjusted as agents observe new targets. Such an iterative process reduces the number of forward passes, thereby improving the method’s computational efficiency.

The main limitation of this approach is the fixed observation size of the current architecture, which limits the number of targets as well as the team size, thus restricting scalability. The work of Wang et al. [20], which used a graph neural network to learn an embedding for social awareness in a multi-robot team, offers a possible starting point for computing observations that are independent of the number of entities. Another idea is presented by Hafner et al. in DreamerV3 [24], where they showed how to extend an actorcritic approach with an additional auto-encoder to learn a world model representation given an instantaneous partial observation of the agent.

## Conclusion

This work explored a reinforcement learning approach to the multi-agent global path planning and scheduling problem, where agents learn an emergent strategy for team coordination and scheduling to efficiently solve a set of targets on a grid. Using a MAPPO-based centralized training framework, we derived decentralized policies that achieved near-optimal solution quality. We observed that with a learning-based method, the complexity of the problem is shifted from runtime to training time. This property can be especially interesting for real-time systems with limited onboard compute, as inference requires only constant-time forward passes. Furthermore, the policy demonstrated the ability to online replanning by using the observation as a buffer for newly incoming targets. Looking forward, a key step toward generalization and scalability is to design an observation structure that is independent of the number of agents and targets. Such representations would enable the discovery of a general policy applicable to different team sizes, numbers of targets, and skill compositions.

## References

[1] P. Arm, H. Kolvenbach, and M. Hutter, “Comparison of legged singlerobot and multi-robot planetary analog exploration systems,” in IAC 2023 Conference Proceedings. International Astronautical Federation, 2023, p. 78381.

[2] J. Balaram, M. M. Aung, and M. P. Golombek, “The ingenuity helicopter on the perseverance rover,” Space Science Reviews, vol. 217, 2021.

[3] P. Arm, G. Waibel, J. Preisig, T. Tuna, R. Zhou, V. Bickel, G. Ligeza, T. Miki, F. Kehl, H. Kolvenbach, and M. Hutter, “Scientific exploration of challenging planetary analog environments with a team of legged robots,” Science Robotics, vol. 8, 2023.

[4] J. R. S´ anchez-Ib´ a˜ nez, C. J. P´ erez-Del-pulgar, and A. Garc´ ıa-Cerezo, “Path planning for autonomous mobile robots: A review,” Sensors, vol. 21, 2021.

[5] J. Richter, H. Kolvenbach, G. Valsecchi, and M. Hutter, “Multiobjective global path planning for lunar exploration with a quadruped robot,” 2023.

[6] O. Cheikhrouhou and I. Khoufi, “A comprehensive survey on the multiple traveling salesman problem: Applications, approaches and taxonomy,” 2021.

[7] M. Vali and K. Salimifard, “A constraint programming approach for solving multiple traveling salesman problem,” 2017.

[8] K. Sundar and S. Rathinam, “Algorithms for heterogeneous, multiple depot, multiple unmanned vehicle path planning problems,” J. Intell. Robotics Syst., vol. 88, no. 2–4, p. 513–526, 2017.

[9] H. Ma and S. Koenig, “Optimal target assignment and path finding for teams of agents,” 2016.

[10] M. Turpin, N. Michael, and V. Kumar, “Concurrent assignment and planning of trajectories for large teams of interchangeable robots,” in 2013 IEEE International Conference on Robotics and Automation. IEEE, 2013, pp. 842–848.

[11] Y. Shuai, S. Yunfeng, and Z. Kai, “An effective method for solving multiple travelling salesman problem based on nsga-ii,” Systems Science and Control Engineering, vol. 7, pp. 121–129, 2019.

[12] A. K. Pamosoaji and D. B. Setyohadi, “Novel graph model for solving collision-free multiple-vehicle traveling salesman problem using ant colony optimization,” Algorithms, vol. 13, 2020.

[13] X. Dong, Q. Lin, M. Xu, and Y. Cai, “Artificial bee colony algorithm with generating neighbourhood solution for large scale coloured traveling salesman problem,” IET Intelligent Transport Systems, vol. 13, pp. 1483–1491, 2019.

[14] V. Pandiri and A. Singh, “A swarm intelligence approach for the colored traveling salesman problem,” Applied Intelligence, vol. 48, pp. 4412–4428, 2018.

[15] Y. Jiang, H. Yedidsion, S. Zhang, G. Sharon, and P. Stone, “Multi-robot planning with conflicts and synergies,” Autonomous Robots, vol. 43, 2019.

[16] Y. Hu, Y. Yao, and W. S. Lee, “A reinforcement learning approach for optimizing multiple traveling salesman problems over graphs,” Knowledge-Based Systems, vol. 204, 2020.

[17] Y. Guo, Z. Ren, and C. Wang, “imtsp: Solving min-max multiple traveling salesman problem with imperative learning,” 2024.

[18] G. Sartoretti, J. Kerr, Y. Shi, G. Wagner, T. K. S. Kumar, S. Koenig, and H. Choset, “Primal: Pathfinding via reinforcement and imitation multi-agent learning,” IEEE Robotics and Automation Letters, vol. 4, no. 3, p. 2378–2385, Jul. 2019. [Online]. Available: http://dx.doi.org/10.1109/LRA.2019.2903261

[19] Zhiyaoa and Sartoretti, “Deep reinforcement learning based multiagent pathfinding,” 2020.

[20] W. Wang, L. Mao, R. Wang, and B.-C. Min, “Multi-robot cooperative socially-aware navigation using multi-agent reinforcement learning,” 2023.

[21] C. Yu, A. Velu, E. Vinitsky, J. Gao, Y. Wang, A. Bayen, and Y. Wu, “The surprising effectiveness of ppo in cooperative, multiagent games,” 2021.

[22] R. Lowe, Y. Wu, A. Tamar, J. Harb, P. Abbeel, and I. Mordatch, “Multi-agent actor-critic for mixed cooperative-competitive environments,” 2017.
