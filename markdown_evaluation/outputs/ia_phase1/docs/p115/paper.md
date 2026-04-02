---
title: "OccAny: Generalized Unconstrained Urban 3D Occupancy"
paper_id: 115
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/.ia_phase1_data/pdfs/8f8c9e275748b72e.pdf"
generated_at: "2026-04-02T01:28:10.892533+00:00"
num_figures: 0
num_tables: 0
num_equations: 0
---

Anh-Quan Cao Tuan-Hung Vu

## Abstract

Abstract

Sequence/Monocular
3D Occupancy
Segmentation

Prompt

Relying on in-domain annotations and precise sensor-rig priors, existing 3D occupancy prediction methods are limited in both scalability and out-of-domain generalization. While recent visual geometry foundation models exhibit strong generalization capabilities, they were mainly designed for general purposes and lack one or more key ingredients required for urban occupancy prediction, namely metric prediction, geometry completion in cluttered scenes and adaptation to urban scenarios. We address this gap and present OccAny, the first unconstrained urban 3D occupancy model capable of operating on out-of-domain uncalibrated scenes to predict and complete metric occupancy coupled with segmentation features. OccAny is versatile and can predict occupancy from sequential, monocular, or surround-view images. Our contributions are three-fold: (i) we propose the first generalized 3D occupancy framework with (ii) Segmentation Forcing that improves occupancy quality while enabling mask-level prediction, and (iii) a Novel View Rendering pipeline that infers novel-view geometry to enable test-time view augmentation for geometry completion. Extensive experiments demonstrate that OccAny outperforms all visual geometry baselines on 3D occupancy prediction task, while remaining competitive with in-domain self-supervised methods across three input settings on two established urban occupancy prediction datasets. Our code is available at https://github.com/valeoai/OccAny .

## Introduction

The innate ability to see and make sense of the world in three dimensions underpins how humans understand and navigate the space. Advancing 3D scene understanding is crucial for spatial intelligent systems such as autonomous driving, robotics, and augmented reality. A key task in this area is 3D occupancy prediction whose goal is to infer a voxelized map of the environment and, when required, provide the corresponding semantics. Despite advances in architecture design [12, 46, 58, 72], training algorithm [5, 27, 30, 44, 76]

Surround

Instances

Prompt

Instances

Figure 1. OccAny is a generalized 3D occupancy model that is
trained once and can operate on out-of-domain sequential, monoc-
ular, or surround-view urban images. It produces SAM2-like fea-
tures, enabling promptable segmentation.

and dataset [4, 10, 13, 18], current state-of-the-art 3D models still lack the generalization of human perception, typically requiring constrained setup with precise sensor calibration. While humans can effortlessly infer complex 3D structures in any novel scenes, replicating this capability remains a demanding problem. State-of-the-art supervised approaches for 3D occupancy prediction [23, 32, 34, 67, 69, 76, 82] achieve remarkable results when the training and test data are drawn from the same distribution, i.e. both are collected using the same or a similar sensor rig under comparable conditions. A core component of these methods is the lifting of 2D features into 3D space, performed either via learnable mechanisms [23, 34] or via explicit camera modeling [5, 79]. However, this lifting operation inherently embeds sensor- and domain-specific biases into the models, which limits their ability to generalize to new sensor suites or environments. Recent self-supervised works [6, 15, 24, 28, 70] remove the need for 3D supervision by formulating occupancy prediction as a differentiable volume-rendering problem, thereby leveraging advances in neural rendering [30, 44]. Despite this, self-supervised models still struggle to generalize, as they remain specialized to a particular training domain with strong biases in camera poses and intrinsic parameters. As we look toward a near future with millions of autonomous fleets equipped with different sensor configurations, advancing 3D occupancy prediction requires generalizable and efficient solutions capable of leveraging heterogeneous training data to overcome

current generalization barriers. The advent of visual geometry foundation models [3, 63,

65, 66], built around the concept of direct pointmap prediction, has demonstrated the strong generalization potential of large-scale transformer networks for 3D scene understanding. However, their general-purpose design remains insufficient for urban occupancy prediction, which simultaneously requires metric-scale accuracy, cluttered geometry completion, and adaptation to the complex nature of urban environments. We introduce a novel pipeline for urban 3D occupancy prediction that emphasizes scalability and generalization. Our approach follows the recipe of geometry foundation models that train visual transformers with straightforward point-level objectives on diverse, large-scale datasets. Unlike those prior works, we specialize in the task of occupancy prediction and focus exclusively on outdoor urban datasets, which we argue is essential for optimal adaptation to the unique characteristics of urban scene perception. A major challenge in outdoor urban scenarios is the sparsity of supervised LiDAR point clouds, which leads to irregular predictions in non-supervised regions and exacerbates the difficulty of geometry completion, particularly in highly cluttered areas. To address this, we introduce Segmentation Forcing, a distillation strategy that enriches geometry-focused features with segmentation awareness and thus helps regularize predictions with consistent segmentation cues of object instances and homogeneous regions. For geometry completion, we develop a Novel View Rendering pipeline that infers arbitrary novel-view geometry from a global scene memory. Our rendering pipeline enables Test-time View Augmentation, allowing us to densify and complete scenes at both the pointand voxel-levels. Fig. 1 illustrates our model. In summary, our contributions are three-fold: • We propose a generalized 3D occupancy framework, OccAny, the first designed to infer dense 3D occupancy and segmentation features for out-of-domain unconstrained urban scenes. A unified OccAny model can operate on either sequential, monocular or surround-view images.

• We introduce Segmentation Forcing, a novel regularization strategy to mitigate the sparsity of LiDAR supervision.

• We develop a Novel View Rendering pipeline targeting geometry completion. OccAny is trained on five urban datasets and evaluated on two out-of-distribution occupancy datasets: SemanticKITTI and Occ3D-NuScenes. OccAny significantly outperforms baseline visual geometry networks and performs on par with domain-specific SOTA self-supervised occupancy networks trained directly on SemanticKITTI and Occ3D-NuScenes.

## Related works

Visual geometry foundation model. Dust3r [66] introduced the visual geometry foundation model, which uses large-scale pointmap prediction to solve diverse 3D tasks.

Research has rapidly expanded this paradigm beyond static, binocular inputs in several directions. One branch addresses dynamics by handling moving scenes [54, 84], dynamic video pose estimation [71], and camera rigs [33]. A major thrust has been multi-frame processing through feed-forward, sequential, and memory-based architectures [3, 62, 63, 65, 77]. Other works have explored downstream tasks such as indoor instance prediction [89] and image matching [31], or have leveraged known camera parameters [26]. While some methods explore novel view synthesis [29, 65], they often prioritize image synthesis over geometric fidelity [29] or exhibit limited applicability [65]. Unlike these approaches, we repurpose these models for occupancy prediction by introducing segmentation forcing to enhance geometric fidelity while enabling segmentation output. We further propose a novel pointmap rendering pipeline to enable complete geometry beyond visible scenery. 3D occupancy prediction . This task, which originates from 3D scene completion [53], aims to assign an occupancy state to each voxel in a 3D volume. Initially proposed for indoor depth scenes [53], it expanded to outdoor LiDAR [1, 7, 49, 73] and was later adapted for multi-view images [5]. Subsequent supervised research has focused on projection mechanisms [5, 34, 79], efficient representations [23, 25, 37, 51, 88], network architectures [34, 41, 85], and benchmark creation [35, 40, 59]. However, these methods’ reliance on dense, voxel-wise annotations limits their scalability. Self-supervised methods mitigate this label dependency by training on posed images, often via volume rendering [6, 70]. Subsequent NeRF-based approaches have improved performance through better losses [21, 24, 83], optimized ray sampling [6, 75, 83], and enhanced representations by distilling foundation models [27, 52, 64]. More recently, 3D Gaussian Splatting has emerged as a more efficient alternative to NeRF [9, 15]. However, these approaches generally require precise camera information and in-domain training data. [15] is a partial exception, avoiding 6D poses via camera overlap, but still requires camera intrinsics and domain-specific information (i.e., adjacent camera overlap). Other works [28, 43, 80, 87] focus on pseudo-label generation, using open-vocabulary foundation models [28, 87] and sequence-level bundle adjustment [43]. While models trained on these pseudo-labels show promising cross-dataset generalization, they remain limited to specific settings.

## Method

We build OccAny, a 3D occupancy framework that can generalize to arbitrary out-of-domain urban scenes. To this end, we adopt the transformer architecture from the Dust3r family and train the model on multiple urban datasets using standard point-level objectives commonly employed in prior works [3, 63, 66]. OccAny is supervised with metric-scale point-clouds enabling metric predictions at test time, a key

Novel-View Rendering
3D Reconstruction

Poses

SAM2

Loss

Frozen

LiDAR

Trainable

element in occupancy prediction. We propose two novel strategies Segmentation Forcing and Novel View Rendering to accommodate the unique characteristics of 3D occupancy prediction in urban environments. Fig. 2 illustrates OccAny training process, which consists of two stages: 3D Reconstruction and Novel View Rendering. For each frame sequence, we randomly select N frames for training. In the reconstruction stage, we set the number of reconstruction frames to N rec = N. In the rendering stage, we use non-overlapping sets of N rec reconstruction frames and N rnd rendering frames, with N = N rec + N rnd.

### 3D Reconstruction with Segmentation Forcing

Projection

LiDAR

SAM2

• SAM2-like feature maps F i ∈ R H′×W ′×C, • global pointmaps P global i,1 ∈ R H×W ×3 in the global camera coordinate of the reference frame 1,

• confidence maps C i ∈ R H×W, • and camera poses v i ∈ R 7 inferred by registering the global and local pointmaps. For each frame i ∈ [3, N rec], a scene memory M i−1 of all historical reconstruction frames 1..i − 1 is used in the decoding process to infer the geometry of the current frame i via cross-attention between tokens of frame i and memory tokens in M i−1. The scene memory M i is then constructed by concatenating M i−1 with the decoder tokens of the current frame i. To initialize, M 2 is formed by concatenating the decoder tokens of the first two frames. With a slight abuse of notation, we use M without a subscript to denote the final global scene memory, which aggregates information from the entire sequence; that is, M ≡ M N rec ∈ R H′×W ′×(C·N rec). The decoder is followed by linear heads for pointmap and confidence prediction, and an MLP head for SAM2-like feature prediction. Because the geometry and segmentation tasks differ in nature, we introduce two learnable task tokens: t g for the pointmap heads and t s for the SAM2 head. These tokens are added to all decoder tokens before the corresponding head is applied. For clarity, we omit task tokens in the equations and only visualize them in Fig. 2. The SAM2 head consists of an MLP with two linear layers followed by two upsampling layers. Each upsampling layer uses bilinear interpolation to resize the features, followed by a convolution, layer norm, and GELU. In summary, the output of this stage is:

### Novel-View Rendering

Reconstruction view

Novel view

Interpolate

Novel-View Rendering with TTVA

3D Occupancy

### OccAny Inference

### Training Losses

Both stages are trained using the same set of losses, i.e. global- and local- pointmap loss L glo, L loc, and Segmentation Forcing loss L forcing, with the exception of the rendering encoder distillation loss L enc, which is applied only in the rendering stage. We only describe common losses in the reconstruction stage for brevity. Pointmap Losses L glo, L loc. The loss weights the difference between the predicted pointmap P global i,1 and ground truth P∗ i,1 using the predicted confidence map C i [3]:

where ⊙ denotes element-wise multiplication with channelwise broadcasting, and α controls the regularization strength, and s is the normalization scale [3, 65]. The local pointmap loss L loc is formulated identically. Geometry-aware Segmentation Forcing Loss L forcing. We employ a Mean Squared Error (MSE) loss. We use the same confidence map C in pointmap losses above to weight the MSE error:

C i ⊙ (F i − F∗
i)

H
′W
′

## Experiments

Training. OccAny is trained on a mixture of five urban datasets, using images from all cameras and projected Li- DAR pointmap as ground truth: Waymo [55], DDAD [19], PandaSet [74], VKITTI2 [2], and ONCE [42]. In the reconstruction stage, we initialize with MUSt3R [3], freeze the encoder E and only train the

decoder D for 3D reconstruction. Input frames are resized to 512-width with varying aspect ratios. We sample training sequences with minimum length N=6 and maximum length N=10. Frames are sampled at 2Hz in all datasets. In the rendering stage, we initialize e D with the pretrained weights of D. We keep the same sequence length N ∈ [6, 10], and randomly select among those N rnd frames as rendering views; the remaining N rec = N − N rnd are used for reconstruction. The first frame serves as reference and it is always part of the reconstruction set. Evaluation. We evaluate the generalization of OccAny on two out-of-domain benchmarks: SemanticKITTI [1] and Occ3D-NuScenes [59], detailed in Sec. A. We use three evaluation settings:

• Sequence: a sequence of 5 frames coming from a single camera on SemanticKITTI and Occ3D-NuScenes,

Figure 4. Occupancy predictions of OccAny and baselines on a sequence and a surround view. We visualize here predicted voxels. For
qualitative analysis, we overlay the semantic ground-truth colors on predicted voxels to better highlight class-wise gains. False positive
voxels are painted in gray without any overlayed color. Compared to baselines, our occupancy predictions are denser and more accurate.

Prec. Rec.
Prec. Rec.

Method
Venue
Semantic KITTI
Occ3D-NuScenes

OccAnybase: w/o Segmentation Forcing & Novel-view Rendering.

Table 1.
Sequence setting.
Occupancy prediction on Se-
manticKITTI and Occ3D-NuScenes.

(IoU) to assess geometry quality; mean IoU (mIoU) is used for semantic segmentation. Following open-vocabulary Li- DAR semantic segmentation works [17, 45, 50], we also report performance on super classes, denoted as mIoU sc. This helps evaluate results at a coarser semantic level, alleviating the impact of “prompting and text-to-image alignment” limitations [45] especially on semantically confusing classes, e.g., “car” vs. “other-vehicle”.

### Main results

Sequence. In the Sequence setting ( Tab. 1), OccAny surpasses all other zero-shot baselines. On SemanticKITTI, it reaches 25.91% IoU, surpassing the nearest baseline

Test Method
Venue
Prec. Rec.

out-of-domain

OccAnybase: w/o Segmentation Forcing & Novel-view Rendering.

Table 2. Monocular setting. Occupancy results with Monocular
input on SemanticKITTI following [6, 24]. Results for MonoScene
and Splatter Image are taken from [6, 75].

(CUT3R*) by roughly 10 points. A similar trend is observed on Occ3D-NuScenes, where OccAny achieves 23.55% IoU, significantly outperforming baselines; of note, some baselines are already enhanced with post-hoc metric scaling and, if applicable, TTVA. This demonstrates OccAny’s ability to effectively complete geometry from limited-view sequence without in-domain training, thanks to Segmentation Forcing

(a) Segmentation Forcing

(b) Novel-View Rendering

Figure 5. Qualitative ablation shows the gains from Segmentation Forcing and Novel-View Rendering. Voxel colorization follows Fig. 4.
The two proposed strategies significantly improve the density and the accuracy of occupancy predictions.

Test Method
Venue
Prec.
Rec.

Res. mIoU mIoU sc Res. mIoU mIoU sc

Table 4. Semantic Occupancy Prediction with GSAM2 [48].

ting on SemanticKITTI (Tab. 2), OccAny demonstrates remarkable generalization. It achieves 24.03% IoU, outperforming all other zero-shot baselines by significant margins (e.g., +11.00% IoU over CUT3R* w/ TTVA). Notably, it significantly surpasses several in-domain self-supervised methods like SceneRF (+10.19%); OccAny even surpasses self-supervised SOTAs SelfOcc (+2.06%) and OccNeRF (+1.22%), despite never been trained on SemanticKITTI.

OccAnybase: w/o Segmentation Forcing & Novel-view Rendering.

Table 3. Surround-view setting. More results are in Tab. 8.

and Novel-View Rendering. The OccAny base variant, which is equivalent to fine-tuning MUSt3R on our datasets, was trained without the two proposed strategies and obtained only marginal improvements over baselines. Wrong metric reasoning leads to voxels predicted outside of the scene, significantly degrading the performance. The scale-invariant design of VGGT and AnySplat is not wellsuited for the occupancy task, unlike OccAny with metric prediction by design. The Gaussian Splatting of AnySplat, while favorable for synthesizing compelling images, produces lots of geometric artifacts, thereby hallucinating lots of noises and harming geometry prediction. Fig. 4 visualizes the occupancy results. Monocular. In the more challenging Monocular set-

Surround-view. In the Surround-view setting on Occ3D- NuScenes Tab. 3, OccAny maintains its lead among zeroshot methods with 34.15% IoU, and achieves better performance than some in-domain approaches like Distill- NeRF/SimpleOcc, yet remains behind more recent methods.

Semantic Occupancy. We further evaluate 3D semantic occupancy (Tab. 4) by applying Grounded SAM2 pipeline directly on OccAny’s segmentation features. OccAny achieves the highest mIoU and mIoU sc across both datasets, compared to baselines using a separated SAM2 model to produce segmentation features. The comparison with the variant “OccAny w/o forcing + SAM2” confirms that our Segmentation Forcing strategy leads to a unified and simpler solution to

Res. Pre. Rec. IoU mIoU mIoU sc Res. Pre. Rec. IoU mIoU mIoU sc

Table 5. Changing the base foundation models used in OccAny
to DA3 [36] and SAM3 [8] results in the OccAny+ variant.

SemKITTI seq.
SemKITTI single

NVR

geo-aware

Table 6. Ablation results on SemanticKitti. The “geo-aware”
stands for applying geometry confidence maps C in the segmenta-
tion forcing loss (cf. Eq. (3)).

25.91

+lateral move

Figure 6. Ablating NVR inference on SemanticKITTI

better predict geometry and segmentation. Impact of base foundation models. We change the foundation models used in OccAny to DA3 [36] and SAM3 [8], resulting in the OccAny+ variant, detailed in Sec. A.3. Tab. 5 and Sec. B show that OccAny benefits from advances in generic foundation models, while being independently and orthogonally effective for occupancy prediction.

### Analysis

Method ablation. Tab. 6 analyzes the contribution of each proposed component. Removing Test-Time View Augmentation (TTVA) causes the most significant drop (−6.27% in sequence- and −12.47% in monocular setting), highlighting its critical role in geometry completion. The renderingspecific losses L Enc, geometry-aware L forcing, and the task tokens also consistently contribute to the final performance, proving their effectiveness. Fig. 5 shows gains brought by Segmentation Forcing and Novel-view Rendering (TTVA). NVR inference. We ablate NVR inference in Fig. 6. Starting from the baseline without TTVA, adding simple forward movement helps complete distant geometry (+1.83%). Introducing rotations and lateral shifts further helps complete the geometry by resolving occlusions from diverse views, improving IoU by +4.15% and resulting in the final 25.91%. Promptable segmentation feature. We visualize the seg-

Figure 7. PCA visualization of our segmentation features of
multi-view sequences. Low-resolution features capture high-level
semantics (e.g., separating cars, buildings, and roads), while high-
resolution features capture low-level details such as boundaries and
textures. Features remain consistent across different views.

Input
Instance Seg.
Input
Instance Seg.

Figure 8. Instance segmentation of cars with OccAny’s features.

mentation features of OccAny using PCA, as shown in Fig. 7. Low-resolution features appear to cluster semantically similar regions, while high-resolution features seem to capture fine details like boundaries and textures, both helping regularize and improve occupancy prediction (cf. Fig. 5 & Tab. 6). Similar to SAM2, our segmentation features remain spatially and temporally consistent. This consistency enables instance segmentation via prompting with object instances detected by Grounding DINO. In Fig. 8, we show some qualitative results when performing instance segmentation directly on our segmentation features.

## Conclusion

We propose for the first time a generalized 3D occupancy network, called OccAny, that is trained once and perform zeroshot inference on arbitrary out-of-domain sequential, monocular and surround-view unposed data. With the proposed Segmentation Forcing and Novel-View Rendering strategies, OccAny outperforms generic visual-geometry foundation models on occupancy prediction. OccAny surpasses several in-domain self-supervised models, while remaining behind more recent ones. Our work introduces a novel framework for occupancy prediction prioritizing scalability and generalization, paving the way toward the next generation of versatile and generalized occupancy networks. The gap to fully-supervised in-domain performance remains substantial, leaving room for future improvements in this direction.

Acknowledgment. This work was granted access to the HPC resources of IDRIS under the allocations AD011014102R2, AD011013540R1 made by GENCI. We acknowledge EuroHPC Joint Undertaking for awarding the project ID EHPC-REG-2025R01-032 access to Karolina, Czech Republic.

## References

[1] Jens Behley, Martin Garbade, Andres Milioto, Jan Quenzel, Sven Behnke, Cyrill Stachniss, and Juergen Gall. Semantickitti: A dataset for semantic scene understanding of lidar sequences. In ICCV, 2019. 2, 5, 13

[2] Yohann Cabon, Naila Murray, and Martin Humenberger. Virtual kitti 2. In arXiv, 2020. 5

[3] Yohann Cabon, Lucas Stoffl, Leonid Antsfeld, Gabriela Csurka, Boris Chidlovskii, Jerome Revaud, and Vincent Leroy. Must3r: Multi-view network for stereo 3d reconstruction. In CVPR, 2025. 2, 3, 5, 6, 7

[4] Holger Caesar, Varun Bankiti, Alex H. Lang, Sourabh Vora, Venice Erin Liong, Qiang Xu, Anush Krishnan, Yu Pan, Giancarlo Baldan, and Oscar Beijbom. nuscenes: A multimodal dataset for autonomous driving. In CVPR, 2020. 1, 13

[5] Anh-Quan Cao and Raoul de Charette. Monoscene: Monocular 3d semantic scene completion. In CVPR, 2022. 1, 2, 5, 6

[6] Anh-Quan Cao and Raoul de Charette. Scenerf: Selfsupervised monocular 3d scene reconstruction with radiance fields. In ICCV, 2023. 1, 2, 6, 13

[7] Anh-Quan Cao, Angela Dai, and Raoul de Charette. Pasco: Urban 3d panoptic scene completion with uncertainty awareness. In CVPR, 2024. 2

[8] Nicolas Carion, Laura Gustafson, Yuan-Ting Hu, Shoubhik Debnath, Ronghang Hu, Didac Suris, Chaitanya Ryali, Kalyan Vasudev Alwala, Haitham Khedr, Andrew Huang, Jie Lei, Tengyu Ma, Baishan Guo, Arpit Kalla, Markus Marks, Joseph Greer, Meng Wang, Peize Sun, Roman Rädle, Triantafyllos Afouras, Effrosyni Mavroudi, Katherine Xu, Tsung-Han Wu, Yu Zhou, Liliane Momeni, Rishi Hazra, Shuangrui Ding, Sagar Vaze, Francois Porcher, Feng Li, Siyuan Li, Aishwarya Kamath, Ho Kei Cheng, Piotr Dollár, Nikhila Ravi, Kate Saenko, Pengchuan Zhang, and Christoph Feichtenhofer. Sam 3: Segment anything with concepts. In ICLR, 2026. 8

[9] Loick Chambon, Eloi Zablocki, Alexandre Boulch, Mickael Chen, and Matthieu Cord. Gaussrender: Learning 3d occupancy with gaussian rendering. In CVPR, 2025. 2

[10] Angel X Chang, Thomas Funkhouser, Leonidas Guibas, Pat Hanrahan, Qixing Huang, Zimo Li, Silvio Savarese, Manolis Savva, Shuran Song, Hao Su, et al. Shapenet: An informationrich 3d model repository. arXiv, 2015. 1

[11] Dubing Chen, Jin Fang, Wencheng Han, Xinjing Cheng, Junbo Yin, Chenzhong Xu, Fahad Shahbaz Khan, and Jianbing Shen. Alocc: adaptive lifting-based 3d semantic occupancy and cost volume-based flow prediction. In ICCV, 2025.

14, 15

[12] Christopher Choy, JunYoung Gwak, and Silvio Savarese. 4d spatio-temporal convnets: Minkowski convolutional neural networks. In CVPR, 2019. 1

[13] Angela Dai, Angel X Chang, Manolis Savva, Maciej Halber, Thomas Funkhouser, and Matthias Nießner. Scannet: Richlyannotated 3d reconstructions of indoor scenes. In CVPR, 2017. 1

[14] Wanshui Gan, Ningkai Mo, Hongbin Xu, and Naoto Yokoya. A comprehensive framework for 3d occupancy estimation in autonomous driving. IEEE TIV, 2024. 7

[15] Wanshui Gan, Fang Liu, Hongbin Xu, Ningkai Mo, and Naoto Yokoya. Gaussianocc: Fully self-supervised and efficient 3d occupancy estimation with gaussian splatting. In ICCV, 2025.

1, 2, 14

[16] Shenyuan Gao, Jiazhi Yang, Li Chen, Kashyap Chitta, Yihang Qiu, Andreas Geiger, Jun Zhang, and Hongyang Li. Vista: A generalizable driving world model with high fidelity and versatile controllability. In NeurIPS, 2024. 15

[17] Simon Gebraad, Andras Palffy, and Holger Caesar. Leap: Consistent multi-domain 3d labeling using foundation models. In ICRA, 2025. 6

[18] Andreas Geiger, Philip Lenz, and Raquel Urtasun. Are we ready for autonomous driving? the kitti vision benchmark suite. In CVPR, 2012. 1

[19] Vitor Guizilini, Rares Ambrus, Sudeep Pillai, Allan Raventos, and Adrien Gaidon. 3d packing for self-supervised monocular depth estimation. In CVPR, 2020. 5

[20] Mariam Hassan, Sebastian Stapf, Ahmad Rahimi, Pedro M. B. Rezende, Yasaman Haghighi, David Brüggemann, Isinsu Katircioglu, Lin Zhang, Xiaoran Chen, Suman Saha, Marco Cannici, Elie Aljalbout, Botao Ye, Xi Wang, Aram Davtyan, Mathieu Salzmann, Davide Scaramuzza, Marc Pollefeys, Paolo Favaro, and Alexandre Alahi. Gem: A generalizable ego-vision multimodal world model for fine-grained ego-motion, object dynamics, and scene composition control. In CVPR, 2025. 15

[21] Adrian Hayler, Felix Wimbauer, Dominik Muhle, Christian Rupprecht, and Daniel Cremers. S4c: Self-supervised semantic scene completion with neural fields. In 3DV, 2024. 2

[22] Mu Hu, Wei Yin, Chi Zhang, Zhipeng Cai, Xiaoxiao Long, Hao Chen, Kaixuan Wang, Gang Yu, Chunhua Shen, and Shaojie Shen. Metric3d v2: A versatile monocular geometric foundation model for zero-shot metric depth and surface normal estimation. IEEE TPAMI, 2024. 5, 6, 7, 13

[23] Yuanhui Huang, Wenzhao Zheng, Yunpeng Zhang, Jie Zhou, and Jiwen Lu. Tri-perspective view for vision-based 3d semantic occupancy prediction. In CVPR, 2023. 1, 2

[24] Yuanhui Huang, Wenzhao Zheng, Borui Zhang, Jie Zhou, and Jiwen Lu. Selfocc: Self-supervised vision-based 3d occupancy prediction. In CVPR, 2024. 1, 2, 5, 6, 7, 13

[25] Yuanhui Huang, Wenzhao Zheng, Yunpeng Zhang, Jie Zhou, and Jiwen Lu. Gaussianformer: Scene as gaussians for visionbased 3d semantic occupancy prediction. In ECCV, 2024. 2

[26] Wonbong Jang, Philippe Weinzaepfel, Vincent Leroy, Lourdes Agapito, and Jerome Revaud. Pow3r: Empowering unconstrained 3d reconstruction with camera and scene priors. In CVPR, 2025. 2

[27] Aleksandar Jevti´ c, Christoph Reich, Felix Wimbauer, Oliver Hahn, Christian Rupprecht, Stefan Roth, and Daniel Cremers. Feed-forward scenedino for unsupervised semantic scene completion. In ECCV, 2025. 1, 2

[28] Haoyi Jiang, Liu Liu, Tianheng Cheng, Xinjie Wang, Tianwei Lin, Zhizhong Su, Wenyu Liu, and Xinggang Wang. Gausstr: Foundation model-aligned gaussian transformer for self-supervised 3d spatial understanding. In CVPR, 2025. 1, 2, 7

[29] Lihan Jiang, Yucheng Mao, Linning Xu, Tao Lu, Kerui Ren, Yichen Jin, Xudong Xu, Mulin Yu, Jiangmiao Pang, Feng Zhao, Dahua Lin, and Bo Dai. Anysplat: Feed-forward 3d gaussian splatting from unconstrained views. ACM TOG, 2025. 2, 5, 6, 7, 14

[30] Bernhard Kerbl, Georgios Kopanas, Thomas Leimkühler, and George Drettakis. 3d gaussian splatting for real-time radiance field rendering. ACM TOG, 2023. 1, 5

[31] Vincent Leroy, Yohann Cabon, and Jerome Revaud. Grounding image matching in 3d with mast3r. In ECCV, 2024. 2

[32] Bohan Li, Yasheng Sun, Xin Jin, Wenjun Zeng, Zheng Zhu, Xiaoefeng Wang, Yunpeng Zhang, James Okae, Hang Xiao, and Dalong Du. Stereoscene: Bev-assisted stereo matching empowers 3d semantic scene completion. In IJCAI, 2024. 1

[33] Samuel Li, Pujith Kachana, Prajwal Chidananda, Saurabh Nair, Yasutaka Furukawa, and Matthew Brown. Rig3r: Rigaware conditioning for learned 3d reconstruction. In NeurIPS, 2025. 2

[34] Yiming Li, Zhiding Yu, Christopher Choy, Chaowei Xiao, Jose M Alvarez, Sanja Fidler, Chen Feng, and Anima Anandkumar. Voxformer: Sparse voxel transformer for camerabased 3d semantic scene completion. In CVPR, 2023. 1, 2

[35] Yiming Li, Sihang Li, Xinhao Liu, Moonjun Gong, Kenan Li, Nuo Chen, Zijun Wang, Zhiheng Li, Tao Jiang, Fisher Yu, Yue Wang, Hang Zhao, Zhiding Yu, and Chen Feng. Sscbench: A large-scale 3d semantic scene completion benchmark for autonomous driving. In IROS, 2024. 2

[36] Haotong Lin, Sili Chen, Jun Hao Liew, Donny Y. Chen, Zhenyu Li, Guang Shi, Jiashi Feng, and Bingyi Kang. Depth anything 3: Recovering the visual space from any views. arXiv, 2025. 5, 6, 7, 8

[37] Haisong Liu, Haiguang Wang, Yang Chen, Zetong Yang, Jia Zeng, Li Chen, and Limin Wang. Fully sparse 3d panoptic occupancy prediction. In ECCV, 2024. 2

[38] Shilong Liu, Zhaoyang Zeng, Tianhe Ren, Feng Li, Hao Zhang, Jie Yang, Qing Jiang, Chunyuan Li, Jianwei Yang, Hang Su, et al. Grounding dino: Marrying dino with grounded pre-training for open-set object detection. In ECCV, 2024. 4

[39] Ilya Loshchilov and Frank Hutter. Decoupled weight decay regularization. In ICLR, 2019. 13

[40] Junyi Ma, Xieyuanli Chen, Jiawei Huang, Jingyi Xu, Zhen Luo, Jintao Xu, Weihao Gu, Rui Ai, and Hesheng Wang. Cam4docc: Benchmark for camera-only 4d occupancy forecasting in autonomous driving applications. In CVPR, 2024. 2

[41] Qihang Ma, Xin Tan, Yanyun Qu, Lizhuang Ma, Zhizhong Zhang, and Yuan Xie. Cotr: Compact occupancy transformer for vision-based 3d occupancy prediction. In CVPR, 2024. 2

[42] Jiageng Mao, Minzhe Niu, Chenhan Jiang, Hanxue Liang, Jingheng Chen, Xiaodan Liang, Yamin Li, Chaoqiang Ye, Wei Zhang, Zhenguo Li, et al. One million scenes for autonomous driving: Once dataset. In NeurIPS, 2021. 5

[43] R. Marcuzzi, L. Nunes, E.A. Marks, L. Wiesmann, T. Läbe, J. Behley, and C. Stachniss. SfmOcc: Vision-Based 3D Semantic Occupancy Prediction in Urban Environments. RA-L, 2025. 2

[44] Ben Mildenhall, Pratul P. Srinivasan, Matthew Tancik, Jonathan T. Barron, Ravi Ramamoorthi, and Ren Ng. Nerf: representing scenes as neural radiance fields for view synthesis. Commun. ACM, 2021. 1

[45] Aljoša Ošep, Tim Meinhardt, Francesco Ferroni, Neehar Peri, Deva Ramanan, and Laura Leal-Taixé. Better call sal: Towards learning to segment anything in lidar. In ECCV, 2024. 6

[46] Charles R Qi, Hao Su, Kaichun Mo, and Leonidas J Guibas. Pointnet: Deep learning on point sets for 3d classification and segmentation. In CVPR, 2017. 1

[47] Nikhila Ravi, Valentin Gabeur, Yuan-Ting Hu, Ronghang Hu, Chaitanya Ryali, Tengyu Ma, Haitham Khedr, Roman Rädle, Chloe Rolland, Laura Gustafson, Eric Mintun, Junting Pan, Kalyan Vasudev Alwala, Nicolas Carion, Chao-Yuan Wu, Ross Girshick, Piotr Dollár, and Christoph Feichtenhofer. Sam 2: Segment anything in images and videos. In ICLR, 2025. 3, 7

[48] Tianhe Ren, Shilong Liu, Ailing Zeng, Jing Lin, Kunchang Li, He Cao, Jiayu Chen, Xinyu Huang, Yukang Chen, Feng Yan, et al. Grounded sam: Assembling open-world models for diverse visual tasks. In arXiv, 2024. 4, 7

[49] Luis Roldão, Raoul de Charette, and Anne Verroust-Blondet. Lmscnet: Lightweight multiscale 3d semantic completion. In 3DV, 2020. 2

[50] Nermin Samet, Gilles Puy, and Renaud Marlet. Losc: Lidar open-voc segmentation consolidator. In 3DV, 2026. 6

[51] Yiang Shi, Tianheng Cheng, Qian Zhang, Wenyu Liu, and Xinggang Wang. Occupancy as set of points. In ECCV, 2024. 2

[52] Sophia Sirko-Galouchenko, Alexandre Boulch, Spyros Gidaris, Andrei Bursuc, Antonin Vobecky, Patrick Pérez, and Renaud Marlet. Occfeat: Self-supervised occupancy feature prediction for pretraining bev segmentation networks. In CVPR, 2024. 2

[53] Shuran Song, Fisher Yu, Andy Zeng, Angel X Chang, Manolis Savva, and Thomas Funkhouser. Semantic scene completion from a single depth image. In CVPR, pages 1746–1754, 2017. 2

[54] Edgar Sucar, Zihang Lai, Eldar Insafutdinov, and Andrea Vedaldi. Dynamic point maps: A versatile representation for dynamic 3d reconstruction. In ICCV, 2025. 2

[55] Pei Sun, Henrik Kretzschmar, Xerxes Dotiwalla, Aurelien Chouard, Vijaysai Patnaik, Paul Tsui, James Guo, Yin Zhou, Yuning Chai, Benjamin Caine, et al. Scalability in perception for autonomous driving: Waymo open dataset. In CVPR, 2020. 5

[56] Stanislaw Szymanowicz, Chrisitian Rupprecht, and Andrea Vedaldi. Splatter image: Ultra-fast single-view 3d reconstruction. In CVPR, 2024. 6

[57] Zachary Teed and Jia Deng. DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras. In NeurIPS, 2021. 15

[58] Hugues Thomas, Charles R Qi, Jean-Emmanuel Deschaud, Beatriz Marcotegui, François Goulette, and Leonidas J Guibas. Kpconv: Flexible and deformable convolution for point clouds. In ICCV, 2019. 1

[59] Xiaoyu Tian, Tao Jiang, Longfei Yun, Yucheng Mao, Huitong Yang, Yue Wang, Yilun Wang, and Hang Zhao. Occ3d: A large-scale 3d occupancy prediction benchmark for autonomous driving. In NeurIPS, 2023. 2, 5, 13

[60] Alexander Veicht, Paul-Edouard Sarlin, Philipp Lindenberger, and Marc Pollefeys. GeoCalib: Single-image Calibration with Geometric Optimization. In ECCV, 2024. 15

[61] Antonin Vobecky, Oriane Siméoni, David Hurych, Spyros Gidaris, Andrei Bursuc, Patrick Pérez, and Josef Sivic. Pop- 3d: Open-vocabulary 3d occupancy prediction from images. In NeurIPS, 2023. 14

[62] Hengyi Wang and Lourdes Agapito. 3d reconstruction with spatial memory. In 3DV, 2025. 2

[63] Jianyuan Wang, Minghao Chen, Nikita Karaev, Andrea Vedaldi, Christian Rupprecht, and David Novotny. Vggt: Visual geometry grounded transformer. In CVPR, 2025. 2, 5, 6, 7, 15

[64] Letian Wang, Seung Wook Kim, Jiawei Yang, Cunjun Yu, Boris Ivanovic, Steven L. Waslander, Yue Wang, Sanja Fidler, Marco Pavone, and Peter Karkus. Distillnerf: Perceiving 3d scenes from single-glance images by distilling neural fields and foundation model features. In NeurIPS, 2024. 2, 7

[65] Qianqian Wang, Yifei Zhang, Aleksander Holynski, Alexei A Efros, and Angjoo Kanazawa. Continuous 3d perception model with persistent state. In CVPR, 2025. 2, 5, 6, 7

[66] Shuzhe Wang, Vincent Leroy, Yohann Cabon, Boris Chidlovskii, and Jerome Revaud. Dust3r: Geometric 3d vision made easy. In CVPR, 2024. 2

[67] Yu Wang and Chao Tong. H2gformer: Horizontal-to-global voxel transformer for 3d semantic scene completion. In AAAI, 2024. 1

[68] Zehan Wang, Siyu Chen, Lihe Yang, Jialei Wang, Ziang Zhang, Hengshuang Zhao, and Zhou Zhao. Depth anything with any prior. In arXiv, 2025. 14

[69] Yi Wei, Linqing Zhao, Wenzhao Zheng, Zheng Zhu, Jie Zhou, and Jiwen Lu. Surroundocc: Multi-camera 3d occupancy prediction for autonomous driving. In ICCV, 2023. 1

[70] Felix Wimbauer, Nan Yang, Christian Rupprecht, and Daniel Cremers. Behind the scenes: Density fields for single view reconstruction. In CVPR, 2023. 1, 2

[71] Felix Wimbauer, Weirong Chen, Dominik Muhle, Christian Rupprecht, and Daniel Cremers. Anycam: Learning to recover camera poses and intrinsics from casual videos. In CVPR, 2025. 2

[72] Xiaoyang Wu, Li Jiang, Peng-Shuai Wang, Zhijian Liu, Xihui Liu, Yu Qiao, Wanli Ouyang, Tong He, and Hengshuang Zhao. Point transformer v3: Simpler faster stronger. In CVPR, 2024.

[73] Zhaoyang Xia, Youquan Liu, Xin Li, Xinge Zhu, Yuexin Ma, Yikang Li, Yuenan Hou, and Yu Qiao. Scpnet: Semantic scene completion on point cloud. In CVPR, 2023. 2

[74] Pengchuan Xiao, Zhenlei Shao, Steven Hao, Zishuo Zhang, Xiaolin Chai, Judy Jiao, Zesong Li, Jian Wu, Kai Sun, Kun Jiang, et al. Pandaset: Advanced sensor suite dataset for autonomous driving. In ITSC, 2021. 5

[75] Binjian Xie, Pengju Zhang, Hao Wei, and Yihong Wu. Higaussian: Hierarchical gaussians under normalized spherical projection for single-view 3d reconstruction. In ICCV, 2025. 2, 6

[76] Yujie Xue, Huilong Pi, Jiapeng Zhang, Yunchuan Qin, Zhuo Tang, Kenli Li, and Ruihui Li. Sdformer: Vision-based 3d semantic scene completion via sam-assisted dual-channel voxel transformer. In ICCV, 2025. 1

[77] Jianing Yang, Alexander Sax, Kevin J. Liang, Mikael Henaff, Hao Tang, Ang Cao, Joyce Chai, Franziska Meier, and Matt Feiszli. Fast3r: Towards 3d reconstruction of 1000+ images in one forward pass. In CVPR, 2025. 2

[78] Lihe Yang, Bingyi Kang, Zilong Huang, Zhen Zhao, Xiaogang Xu, Jiashi Feng, and Hengshuang Zhao. Depth anything v2. In NeurIPS, 2024. 15

[79] Jiawei Yao, Chuming Li, Keqiang Sun, Yingjie Cai, Hao Li, Wanli Ouyang, and Hongsheng Li. Ndc-scene: Boost monocular 3d semantic scene completion in normalized device coordinates space. In ICCV, 2023. 1, 2

[80] Baijun Ye, Minghui Qin, Saining Zhang, Moonjun Gong, Shaoting Zhu, Hao Zhao, and Hang Zhao. Gs-occ3d: Scaling vision-only occupancy reconstruction with gaussian splatting. In ICCV, 2025. 2

[81] Zhangchen Ye, Tao Jiang, Chenfeng Xu, Yiming Li, and Hang Zhao. Cvt-occ: Cost volume temporal fusion for 3d occupancy prediction. In ECCV, 2024. 14, 15

[82] Zhu Yu, Runmin Zhang, Jiacheng Ying, Junchen Yu, Xiaohai Hu, Lun Luo, Si-Yuan Cao, and Hui-liang Shen. Context and geometry aware voxel transformer for semantic scene completion. In NeurIPS, 2024. 1

[83] Chubin Zhang, Juncheng Yan, Yi Wei, Jiaxin Li, Li Liu, Yansong Tang, Yueqi Duan, and Jiwen Lu. Occnerf: Advancing 3d occupancy prediction in lidar-free environments. IEEE TIP, 2025. 2, 6, 7

[84] Junyi Zhang, Charles Herrmann, Junhwa Hur, Varun Jampani, Trevor Darrell, Forrester Cole, Deqing Sun, and Ming-Hsuan Yang. Monst3r: A simple approach for estimating geometry in the presence of motion. In ICLR, 2025. 2

[85] Yunpeng Zhang, Zheng Zhu, and Dalong Du. Occformer: Dual-path transformer for vision-based 3d semantic occupancy prediction. In ICCV, 2023. 2

[86] Jilai Zheng, Pin Tang, Zhongdao Wang, Guoqing Wang, Xiangxuan Ren, Bailan Feng, and Chao Ma. Veon: Vocabularyenhanced occupancy prediction. In ECCV, 2024. 14

[87] Xiaoyu Zhou, Jingqi Wang, Yongtao Wang, Yufei Wei, Nan Dong, and Ming-Hsuan Yang. Autoocc: Automatic openended semantic occupancy annotation via vision-language guided gaussian splatting. In ICCV, 2025. 2

[88] Sicheng Zuo, Wenzhao Zheng, Xiaoyong Han, Longchao Yang, Yong Pan, and Jiwen Lu. Quadricformer: Scene as superquadrics for 3d semantic occupancy prediction. NeurIPS, 2025. 2

[89] Lojze Zust, Yohann Cabon, Juliette Marrie, Leonid Antsfeld, Boris Chidlovskii, Jerome Revaud, and Gabriela Csurka. Panst3r: Multi-view consistent panoptic segmentation. In ICCV, 2025. 2

Res. mIoU mIoU sc Res. mIoU mIoU sc

Table 7. Using pretrained segmentation features to boost seman-
tic performance. OccAny+ is the variant using DA3 and SAM3
base models. Parameter counts reflect the forward path from the
input to the predicted pointmaps and segmentation features. Note
that using "pretrained" semantic features incurs a higher parameter
cost due to the use of pretrained encoder.

## Additional Details

### Datasets

Occ3D-NuScenes was built upon nuScenes [4]. It contains 1, 000 20-sec sequences captured by one LiDAR and six surrounding cameras. The dataset provides 3D occupancy annotations of 18 semantic classes, with 0.4 m voxels covering 80×80×6.4 m areas at the resolution of 200×200×16 voxels. Evaluation is done on the official val split [59] of 150 sequences. SemanticKITTI, based on KITTI [1], consists of 22 sequences. Each sequence is annotated at the resolution of 256 × 256 × 32 with 0.2 m voxels and 21 semantic classes (19 semantics, 1 free, 1 unknown). In our experiments, we only use images from the cam2 camera. Following [6, 24], we evaluate on the val set, i.e. sequence 8.

### Training

The 3D Reconstruction stage (cf. Sec. 3.1) is trained in two consecutive steps: • Sequence-only training. We only use mono-view sequences from all cameras across the five datasets. Training samples are drawn from frames within the same monoview sequences.

• Mixed training. This step continues Sequence-only training while mixing surround-view data with sequential data (from the previous step) at a 1 : 1 ratio. For surround-view data, we use frames from different cameras captured at the same timestep. The Novel-View Rendering stage (cf. Sec. 3.2) is trained exclusively on sequential data. Empirically, we observed no gains when incorporating surround-view data in this stage. Each stage is trained for 100 epochs using the AdamW optimizer [39] with a learning rate of 7 × 10−5. We utilize a cosine scheduler with a minimum learning rate of 1×10−6 and a 3-epoch warmup. The training set consists of 50, 000 samples (sequences or sets of surrounding images), with 10, 000 drawn from each dataset. Experiments are conducted on 16 NVIDIA A100 40GB GPUs with an effective batch size of 64. The 3D Reconstruction and Novel-View

GT
LiDAR

Sem.
Adapt.

Fixed
Rig

Fixed
Ratio

Extr.

GT
Occ.

Intr.

SimpleOcc Req. Req. Req. Req. Req. Req. – 33.92 7.05 DistillNeRF Req. Req. Req. Req. Req. – – 29.11 8.93 SelfOcc Req. Req. Req. Req. – Req. – 45.01 9.30 POP-3D Req. Req. Req. Req. Req. Req. – 28.17 9.31 OccNeRF Req. Req. Req. Req. – Req. – 39.20 9.53 GaussianOcc – Req. Req. Req. – Req. – 51.22 9.94 VEON Req. Req. Req. Req. Req. Req. Req. 57.92 12.38 GaussTR Req. Req. Req. Req. – Req. – 45.19 12.27

Occ3D-NuScenes (ext. Tab. 3)

Req.: required in-domain data/priors. Rescale: metric scaling needed

Table 8. Detailed surround-view results. OccAny+ is the variant
using DA3 and SAM3 base models.

Rendering stages required approximately 40 and 30 training
hours, respectively.

### OccAny+ using DA3 and SAM3

## Supplementary Studies

We present here the supplementary studies not presented in the main text due to the lack of space.

### Boosting semantic performance

While the unified OccAny model conveniently uses distilled segmentation features, it can also be combined with the original features from segmentation foundation models at inference. Although this introduces additional overhead, it enables the use of higher-resolution segmentation features and improves semantic performance, as shown in Tab. 7.

### More surround-view results

Tab. 8 details results and method constraints in the surround-view setting, further including POP-3D [61], GaussianOcc [15], and VEON [86]. Existing in-domain approaches, including self-supervised ones, rely heavily on domain-specific priors, and VEON further depends on binary occupancy ground truth for training. In contrast, OccAny promotes a paradigm shift toward generalized and unconstrained occupancy prediction, enabling deployment of a unified model across out-of-domain and heterogeneous sensor setups. Beyond being unconstrained, OccAny can benefit from continual advances in foundation models, and is therefore expected to progressively narrow the remaining performance gap. As preliminary evidence, upgrading MUSt3R to DA3 and replacing SAM2 with the more recent SAM3 yields an mIoU improvement of approximately 3 points, reaching performance comparable to recent self-supervised methods such as GaussianOcc [15].

### Novel-View Rendering vs. Depth Completion

In this experiment, we compare the effectiveness of our Novel-View Rendering stage (cf. Sec. 3.2) with a baseline that performs depth completion on the projected pointmaps of the novel views. To this end, we replace Novel-View Rendering by using Prior Depth Anything [68], which takes as input the sparse projected pointmaps and the rendered RGB images produced by the state-of-the-art novel-view synthesis method AnySplat [29]. The Prior Depth Anything model outputs dense, completed depth maps for the novel views. We name this baseline OccAny depth completion and present comparison results in Tab. 9. Both models start from the first-stageonly OccAny and both adopt the TTVA strategy. OccAny significantly outperforms the OccAny depth completion baseline, validating the effectiveness of our second stage.

### Generalization of State-of-the-art (SOTA) 3D Supervised Occupancy Models

We assess the generalization capability of SOTA 3D fullysupervised models by evaluating models trained on a source

dataset directly on a different target dataset. We evaluate two settings: • Occ3D-Waymo→ Occ3D-NuScenes (surround-view → surround-view).

• Occ3D-NuScenes/Occ3D-Waymo→ SemanticKITTI (surround-view→ monocular). As shown in Table 10, despite careful alignment of sensor configurations, inference areas, and voxel resolutions, these supervised methods exhibit limited generalization capabilities compared to OccAny. Notably, OccAny’s inference is straightforward and does not require any prior knowledge of the sensor configurations (number of cameras, intrinsics/extrinsics and camera poses), adapting effortlessly to any inference areas and any voxel resolutions. Occ3D-Waymo→Occ3D-NuScenes. In this setting, we evaluate CVT-Occ [81] using weights trained on Occ3D-Waymo to perform inference on Occ3D-NuScenes. While the voxel resolutions and voxel sizes are consistent between these datasets, significant differences remain in sensor configurations. To enable inference, we align the sensor setups by mapping the five Occ3D-Waymo cameras to the six Occ3D-NuScenes cameras. Specifically, we map the Occ3D-Waymo Front, Front-Right, and Front-Left to their Occ3D-NuScenes counterparts, while the Occ3D-Waymo Side-Left is mapped to both Back and Back-Left, and Side- Right to Back-Right. Regarding image resolution, we follow the official implementation to scale Occ3D-NuScenes input images to the Occ3D-Waymo training resolution of 960 × 640. We also report inference performance at 1600 × 900, which yields slightly better results. However, as detailed in Table 10, even with these manual adaptations, the model struggles to generalize to the new domain, achieving a peak IoU of only 17.56%, significantly lower than the 34.15% achieved by our method. Occ3D-NuScenes/Occ3D-Waymo→SemanticKITTI. Regarding the transfer from surround-view to monocular, we evaluate two SOTA 3D supervised methods: CVT- Occ [81] and ALOcc [11]. We use checkpoints trained on Occ3D-NuScenes (for both ALOcc and CVT-Occ) and Occ3D-Waymo (for CVT-Occ) to perform inference on SemanticKITTI. This scenario presents a significantly greater challenge than the previous setting: in addition to domain shifts and sensor discrepancies (using only the source front camera to align with the target setup), there are substantial divergences in voxel grid extents and resolutions. For CVT-Occ [81], we use two provided models, one trained on Occ3D-NuScenes (1600 × 900) and another trained on Occ3D-Waymo (960 × 640). We evaluate the Occ3D-NuScenes-trained model on SemanticKITTI at full image resolution (1220 × 370), as it is closely aligned with the training resolution. For the Occ3D-Waymo-trained model, we conduct evaluations at both the full resolution and a resized resolution of 960 × 540, which preserves the

Semantic KITTI
Occ3D-NuScenes

Res. sequence monocular Res. sequence surround-view

Prec. Rec. IoU Prec. Rec. IoU Prec. Rec. IoU Prec. Rec. IoU

Table 9. Novel-View Rendering vs. Depth Completion. Occupancy prediction results on SemanticKITTI and Occ3D-NuScenes show the
effectiveness of Novel-View Rendering.

Table 10. Generalization results of fully-supervised methods. Occ label is denser through temporal accumulation of LiDAR point-clouds
and subsequent post-processing, whereas the LiDAR label remains sparser at each timestep. OccAny works out of the box in any evaluation
settings with different inference areas, voxel resolutions and sensor configurations. In contrast, other methods require manual code
modifications to align testing and training conditions. Beyond being more versatile, OccAny clearly demonstrates superior generalization.

For ALOcc [11], only the model trained on Occ3D-NuScenes is available. Since ALOcc encodes the stereo cost volume’s frustum grid within its parameters, the network is constrained to a fixed input resolution of 704 × 256. Consequently, we evaluate ALOcc on SemanticKITTI at this exact resolution, adhering to the official implementation by using 16 history frames and pairs of consecutive timesteps as stereo input.

The results in Table 10 highlight a significant drop in performance when these models are inferred on the unseen SemanticKITTI dataset. CVT-Occ and ALOcc achieve IoUs of only 9.43% and 14.28%, respectively, whereas our proposed method demonstrates superior robustness with an IoU of 24.03%.

### Ego Vehicle Trajectory Prediction

We assess the quality of ego-trajectory prediction using OccAny on the nuScenes validation set, following the evaluation protocol of [16, 20]. OccAny+ outperforms the base DA3-LARGE model in terms of Average Displacement Error (ADE), demonstrating clear advantages in urban scenes. Furthermore, it approaches the accuracy of optimization-based RGB-D SLAM methods while remaining fully feed-forward and significantly simpler.

Prec.
Rec.
Prec.
Rec.

Table 11. Ego Vehicle Trajectory Prediction.

\#Aug. Frames

Table 12. NVR inference complexity, measured on one A100
GPU.

Table 13. Model size and speed. Train times are from the original
papers. Inference times are measured in the surround setting with 6
input views and 6 render views.

B.6. NVR complexity.

We report in Tab. 12 the memory consumption and running time of NVR inference using one A100 GPU in the surround-view setting. Similar to VGGT (cf. Tab. 9 in [63]), both memory & time scale much slower w.r.t. number of augmentation frames.

We are report the model sizes and speeds of OccAny and baselines in Tab. 13. OccAny has the fewest parameters (∼651M) vs. CUT3R (∼793M) and VGGT/AnySplat (∼1.2B), and is the most runtime efficient in training/inference. OccAny’s rendering is about 2× faster than CUT3R, while AnySplat’s is the fastest thanks to 3DGS.

## Qualitative Examples

We show additional qualitative results in Fig. 9, Fig. 10, Fig. 11, Fig. 12, and Fig. 13.

Figure 9. Occupancy predictions of OccAny and baselines on sequential data. We visualize here predicted voxels. For qualitative analysis,
we overlay the semantic ground-truth colors on predicted voxels to better highlight class-wise gains. False positive voxels are painted in gray
without any overlayed color. Compared to baselines, our occupancy predictions are denser and more accurate.

Figure 10. Occupancy predictions of OccAny and baselines on surround-view data. Voxel colorization follows Fig. 9. Compared to
baselines, our occupancy predictions are denser and more accurate.

Figure 11. Qualitative ablation on Semantic KITTI shows the gains from Segmentation Forcing and Novel-View Rendering. Voxel
colorization follows Fig. 9. The two proposed strategies significantly improve the density and the accuracy of occupancy predictions.

Figure 12. Qualitative ablation on Occ3D-NuScenes shows the gains from Segmentation Forcing and Novel-View Rendering. Voxel
colorization follows Fig. 9. The two proposed strategies significantly improve the density and the accuracy of occupancy predictions.

Figure 13. PCA visualization of predicted feature maps. Low-resolution features capture high-level semantics (e.g., separating cars,
buildings, and roads), while high-resolution features capture low-level details such as boundaries and textures. Features remain consistent
across different views.
