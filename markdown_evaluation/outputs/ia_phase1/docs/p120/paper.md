---
title: "Detailed Geometry and Appearance from Opportunistic Motion"
paper_id: 120
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/.ia_phase1_data/pdfs/41528b7825c49511.pdf"
generated_at: "2026-04-02T01:28:14.685649+00:00"
num_figures: 0
num_tables: 0
num_equations: 0
---

Ryosuke Hirai 1, Kohei Yamashita 1, Antoine Guédon 2,3, Ryo Kawahara 1, Vincent Lepetit 3, and Ko Nishino 1

1 Graduate School of Informatics, Kyoto University, Japan https://vision.ist.i.kyoto-u.ac.jp/ 2 École Polytechnique, France 3 LIGM, École Nationale des Ponts et Chaussées, IP Paris, Univ Gustave Eiffel, CNRS, France

Geometry Appearance

Sparse Static Cameras

Object Motion Effective Dense Viewpoints

Single-Frame Ours Ground Truth

Fig. 1: We introduce a method to recover high-fidelity 3D geometry and appearance from sparse-view static videos. By leveraging “virtual viewpoints” induced by opportunistic object motion, our method jointly optimizes object pose and geometry through a motion-aware appearance representation to capture detailed surface structure.

## Abstract

Abstract. Reconstructing 3D geometry and appearance from a sparse set of fixed cameras is a foundational task with broad applications, yet it remains fundamentally constrained by the limited viewpoints. We show that this bound can be broken by exploiting opportunistic object motion: as a person manipulates an object (e.g., moving a chair or lifting a mug), the static cameras effectively “orbit” the object in its local coordinate frame, providing additional virtual viewpoints. Harnessing this object motion, however, poses two challenges: the tight coupling of object pose and geometry estimation and the complex appearance variations of a moving object under static illumination. We address these by formulating a joint pose and shape optimization using 2D Gaussian splatting with alternating minimization of 6DoF trajectories and primitive parameters, and by introducing a novel appearance model that factorizes diffuse and specular components with reflected directional probing within the spherical harmonics space. Extensive experiments on synthetic and realworld datasets with extremely sparse viewpoints demonstrate that our method recovers significantly more accurate geometry and appearance than state-of-the-art baselines.

Keywords: 3D Reconstruction · Appearance Modeling · Pose Estimation

## Introduction

Multiview 3D object reconstruction has achieved a vertical leap in photorealism with the advent of neural representations, most notably 3D Gaussian Splatting (3DGS) [19]. When dense captures from tens of viewpoints are available via a moving camera, these methods recover stunningly accurate geometry and appearance. Understanding scenes from a sparse set of fixed viewpoints, however, remains a critical challenge for real-world applications, including home safety monitoring for the elderly or children. The logistical ease of installing static cameras in room corners makes it highly compelling for practical deployment. Recovering 3D geometry from sparse, static views is inherently ill-posed. The overlap between visual frusta is often insufficient for traditional stereo algorithms, and while monocular estimation can provide coarse structure, it fails to capture surface-level details. 3D Gaussian Splatting also struggles under such extreme sparsity. Recent methods that combine neural depth priors (e.g. MAtCha [13]) with neural appearance representations improve accuracy via photometric losses, but as we show in Fig. 1 (Single-Frame), they still fail to reconstruct the surface details of individual objects. If the scene remains entirely static, the information available for reconstruction is strictly bounded by the number of cameras and their spatial baseline, typically yielding crude results with sparse views (e.g., four corner cameras). Fortunately, real-world scenes are rarely completely static; the daily activities of a person— picking up a mug, retrieving a book, or moving a chair—unfold continuously. While these movements are often considered a nuisance for 3D reconstruction, they actually provide a wealth of information to recover finer geometric and radiometric details. In this paper, we exploit the movement of an object to recover higher-resolution geometry and appearance from just a handful of static cameras. Two fundamental challenges, however, hamper the use of modern neural representations in this context. First, estimating the relative motion between a target object and a fixed camera is significantly more difficult than standard camera pose estimation. When we have a moving camera, e.g., SLAM or SfM, the entire image including the static background can help determine the camera trajectory. For static cameras with opportunistic object motion, the only cue for estimating the relative camera poses is the object itself. This makes the optimization highly sensitive to the current state of the object geometry. Second, the standard appearance model in 3DGS is no longer valid. In traditional 3DGS, the radiance of a Gaussian is typically modeled by a set of Spherical Harmonics (SH) that remain constant over time. This assumes the lighting environment is “attached” to the object. When an object moves relative to static light sources, this assumption breaks down. For specular surfaces—common in everyday plastic or metallic objects—the appearance changes drastically as the object rotates relative to the surrounding illumination. Using standard SH coefficients under these conditions results in burned-in lighting and, in turn,corrupt the geometry.

We introduce a novel method to jointly estimate the pose, geometry, and appearance of objects observed by a sparse set of static cameras by leveraging their opportunistic movements. We resolve the coupling between pose and shape through an alternating optimization framework and introduce a motion-aware appearance representation that explicitly models radiance changes during object motion. Our model adopts two physically-grounded assumptions frequently met in real-world scenarios: homogeneous specular reflection and distant lighting. Most everyday objects share a common coating that induces uniform glossiness and are small relative to the distance to environmental light sources. Based on these principles, our appearance model accurately captures complex variations for a wide range of practical applications. We demonstrate that by correctly modeling these view-dependent and motiondependent effects, we can leverage object movement to retrieve highly accurate 3D geometry and appearance. We validate our approach on a newly created synthetic dataset and two real-world existing datasets with extremely sparse views, showing that opportunistic motion is a powerful signal for fine-grained reconstruction when handled with a physically-grounded appearance model.

## Related Work

3D Scene Reconstruction has progressed significantly with neural rendering techniques such as NeRF [25] and 3D Gaussian Splatting [19]. These methods require dense captures, typically of tens of viewpoints, to optimize scene representation via differentiable rendering. Subsequent works have further improved rendering quality [2, 3, 5, 26, 34, 44] or focused on extracting explicit surface geometry [7, 12, 15, 36, 38, 45] by leveraging novel representations (e.g., neural SDFs and 2D Gaussians). To relax the requirement of dense capture, several methods [13,24,27,31,33,40] tackle sparse-view reconstruction by incorporating learned geometric priors [13,24,33,40]. The accuracy of these methods, however, remains fundamentally bounded by the number of input viewpoints.

Dynamic 3D Scene Reconstruction often employs deformation networks combined with a 3D representations such as neural networks or 3DGS [28,30,43] to model non-rigid motion. Recent works have specifically focused on extracting surface geometry from these dynamics scenes [4,21,48]. These methods, however, typically assume videos with extensive camera motion to provide the necessary multiview information for fine reconstruction. Such requirements limit their applicability in real-world scenarios, such as fixed-camera monitoring. They also often require known camera poses for all moving frames, which is difficult to estimate in dynamic settings. In contrast, our method requires only a sparse set of static, calibrated cameras. Another research line focuses on rigidly moving objects to recover both rigid object motion and 3D structure. Although joint pose estimation and reconstruction like Jin et al. [18] and Wen et al. [39] show promise, they rely on direct depth measurements (RGB-D) which are often unavailable. In RGB-only settings like ours, current approaches often leverage category-specific priors (e.g., hand-object

interaction) [6, 16], recover only coarse volumetric density [37, 46], or assume highly-textured surfaces for pose tracking [22]. Our framework overcomes these limitations by explicitly modeling the specular effects that emerge from the relative motion between lighting, geometry, and cameras. This allows our method to handle texture-sparse objects and achieve high-fidelity 3D reconstructions.

Appearance Modeling for Specular and Dynamic Objects is indeed challenging for neural object representations. For static objects, recent works have tackled this with specialized radiance functions or inverse rendering for lighting and material parameters [10, 11, 17, 20, 23, 35, 49]. In dynamic scenes, however, appearance depends on both view and motion. While some methods attempt to handle specularity in dynamic settings [9,41], they typically estimate complex, spatially-varying appearance parameters for every 3D surface point (e.g., each Gaussian primitive). This estimation becomes under-constrained for sparse observations, as in our case. Our approach derives a compact yet expressive appearance model that considers pose-dependent changes in both diffuse and specular reflections. By evaluating spherical harmonics via the reflected view direction, we enable accurate geometry and appearance reconstruction from sparse observations.

## Preliminaries: Gaussian Splatting

where Y m l (v) denotes an SH basis function. The Gaussian parameters (µ i, q i, s i, σ i, and θ i) are optimized through a differentiable tile-based rasterizer. 2D Gaussian splatting [15] is a variant for accurate geometry reconstruction. It represents a 3D scene with oriented planar Gaussian primitives. Each 2D Gaussian is characterized by a surface normal n i and a 2D scale, facilitating perspective-consistent depth evaluation and accurate surface extraction. These surface normals allow for direct geometric regularization—such as depth-normal consistency losses—and, as we show later, provide the necessary geometric context to model complex view- and pose-dependent appearance for moving objects.

Canonical
Gaussians

Canonical
Gaussians

Sparse Multi-View Videos

ℒ refine

RGB Observations
+ Geometry Priors

Segmentation

Segmentation

Canonical Gaussians with Mask

Mask

Observations

Mask

(b) Object pose estimation

(c) Gaussian Refinement

Fig. 2: Method Overview. Given sparse multi-view videos and an initial set of canonical
2D Gaussians (a), our framework recovers per-frame object poses while iteratively
refining the Gaussian geometry via differentiable rendering. To ensure robust convergence
under sparse supervision, we employ an alternating optimization that switches between
6-DoF object pose estimation (b) and canonical Gaussian refinement (c) using the
aggregated temporal information from all processed frames.

duce a compact yet expressive appearance model that accounts for view- and pose-dependent appearance changes throughout the sequence.

### Single-Frame 3D Reconstruction with Learned Priors

### Motion-Aware Joint Optimization via Soft-Masked Transform

Using multi-view observations from subsequent timesteps, we alternate between estimating per-frame object poses and refining the canonical Gaussian parameters. In both stages, we transform the canonical Gaussians associated with the foreground (those with high mask values m i) according to the current pose estimate, render the scene, and back-propagate photometric gradients. A significant challenge is that initial mask values may be noisy, potentially degrading estimation accuracy. We address this by refining the per-Gaussian mask values m i concurrently with object motion. To facilitate this, we derive a soft-masked rigid transformation that allows gradients to flow directly to the mask values. Given the object pose (q t obj, t t obj) and mask values m i ∈ [0, 1], we compute the interpolated motion for each Gaussian:

where R t obj,i is a rotation matrix for q t obj,i and p is the object centroid in the canonical space computed from the initial canonical Gaussians and the initial mask values. Other Gaussian attributes remain fixed to their canonical values. For this phase, we use the standard appearance model (Eq. (1)), but evaluate the viewing direction in the object’s local coordinate system. This effectively assumes a “body-attached” lighting environment, which we further refine in Sec. 4.3. We supervise the optimization using a composite loss function. Following 3DGS [19] and 2DGS [15], we employ a rendering loss L RGB (comprising L 1 and D-SSIM) and a depth-normal consistency loss L n. To ensure stability under sparse views, we integrate the geometric priors from MAtCha [13]: a depth prior loss L pdepth and a normal prior loss L pnormal based on foundation model estimates [8,42]. Finally, to enforce a clear separation between the moving object and the static background, we apply an entropy-based binary regularization on the mask values:

for physically meaningful estimation. The overall loss function for the pose estimation phase L pose and Gaussian refinement phase L refine are defined as follows:

### Motion-Aware Appearance Modeling via Radiance Probing

Following the alternating optimization phase, we perform a joint refinement of geometry and appearance using the full temporal sequence. To achieve highfidelity reconstruction from sparse views, we derive a compact, physically-inspired appearance model tailored for moving objects. As illustrated in Fig. 3a, specular radiance on smooth surfaces primarily depends on the surface reflectance k s and the incident illumination from the reflected viewing direction:

𝐧

𝐧

𝐧

(a) Effective Light for Specular Reflection

(b) Effective Hemisphere for Diffuse Shading

𝐤 𝑑,𝑖

𝐯 𝑖

𝛚 𝑟,𝑖

𝐧 i

𝐧 𝑗

𝐜 𝑠,𝑖

𝐜 𝑑,𝑖

𝐜 𝑖

𝛚 𝑟,𝑗

𝐧 𝑖

𝐤 𝑑,𝑖

𝛚 𝑟,𝑗

𝜃 𝑠

𝐜 𝑠,𝑗

𝐜 𝑗

𝐜 𝑑,𝑗

x

(c) Definition of Inputs

(e) Specular Model

(f) Diffuse Model

Fig. 3: Motion-Aware Appearance Modeling. (a) For moving objects, specular
reflection is a function of incident radiance from the reflected viewing direction ω r,
which evolves with object pose. (b) Similarly, diffuse reflection depends on the time-
varying surface normal n relative to the static environment. (c) Our model factorizes
appearance into specular (e) and diffuse (f) components by evaluating the surface normal
and reflected viewing directions in the world coordinate system. (d) Unlike standard
3DGS, which optimizes independent Spherical Harmonics (SH) for each primitive, our
approach employs shared SH coefficients θ d and θ s across all foreground Gaussians to
robustly capture the global illumination field.

where v and n denote the viewing direction and surface normal in the world coordinate system, respectively. Let ⊙ denote the Hadamard product. We approximate the specular component for each Gaussian (i) as

where k s,i is the specular reflectance and ω r,i is the view direction reflected by the surface normal n i. In effect, this models a Phong-like [29] specular component. f is a weighted sum of SH basis functions. The learnable SH coefficients θ s approximate the incident radiance from the surrounding environment probed by the reflected view direction. Assuming the illumination is distant relative to the object size, the incident radiance remains invariant to surface translation; thus, we employ a single set of SH coefficients θ s shared across all foreground Gaussians. In practice, we set k s,i = 1, i.e., assume objects with uniform gloss. We further account for diffuse reflection, which also exhibits time-dependency as the object rotates through a static lighting environment. The radiance for a Lambertian surface is defined by

where k d is diffuse albedo and L i denotes the incident radiance as a function of incident direction ω i. As depicted in Fig. 3b, this integral is a function of the time-varying surface normal n. We approximate the diffuse component as

where θ d represents the learnable SH coefficients for the diffuse irradiance. Our final appearance model computes the total color as sum of the specular and diffuse components:

Figure 3 (c)-(f) summarizes the differences between the standard 3DGS
appearance model and our motion-aware factorized appearance model. By sharing
SH coefficients across all foreground primitives and only optimizing per-Gaussian
albedo, our model remains highly expressive yet robust to sparse supervision.
Unlike standard 3DGS, which optimizes independent SH coefficients for every
primitive, our model explicitly leverages the geometric relationship between
surface normals and world-space illumination.
In this final refinement stage, we omit the monocular depth and normal prior
losses, as the accumulated temporal observations provide sufficient geometric
constraints. The final optimization objective is:

### Meshing with Viewpoints from All Frames

Once the joint optimization is complete, we extract a surface mesh of the foreground object. We adapt the strategy of MILo [12] to our dynamic setting, allowing the meshing process to leverage observations of the motion at all timesteps rather than relying solely on the canonical frame. We first isolate the foreground Gaussians by thresholding the optimized mask values m i. Each selected Gaussian G i spawns a fixed set of pivot points anchored within its local coordinate frame. Because pivots are anchored to their parent Gaussian, they follow the object through time: at timestep t, each pivot is transformed by the same masked rigid motion as its Gaussian (Eqs. (4) and (5)). A Delaunay triangulation of the pivots yields a volumetric tetrahedral mesh which evolves over time as the pivots move with the object. We assign a learnable signed distance value (SDF) to each pivot and optimize these values over 1000 iterations. At each iteration, we first select a timestep and extract a triangle mesh from the current SDF values and Delaunay triangulation via differentiable marching tetrahedra [1]. Then, we select a viewpoint, render depth and normal maps from the extracted mesh, and compare them to the corresponding depth and normal maps rendered from the Gaussians. Gradients are back-propagated from this rendering loss to the SDF values, enforcing the surface of the dynamic object to match the geometry of the Gaussians. Crucially, this supervision aggregates over all views v and all timesteps t, so that the SDF values benefit from the same effectively dense observations that drove the Gaussian refinement. After convergence, the final mesh is extracted by applying marching tetrahedra to the first frame pivot positions.

Table 1: Surface normal accuracy for synthetic data. We evaluate reconstruction
quality on synthetic data using the mean, median, and 80th percentile errors against
ground-truth surface normals. The results demonstrate that our proposed components
significantly enhance the recovery of fine surface details. While simpler surfaces, such
as the drain cleaner, can be handled by baseline methods, they do not fully reflect our
method’s capability to reconstruct intricate geometric details.

Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓

## Experimental Results

We validate the effectiveness of our method using a newly created synthetic multi-view video dataset and established real-world datasets.

Implementation Details. We implement our framework using a single NVIDIA RTX A6000 GPU (48 GB VRAM). On average, pose estimation and Gaussian refinement require 3 and 4 minutes per frame, respectively, with a total optimization time of approximately 7 hours for a typical sequence. In practice, this can be sped up, e.g., by keyframing during the alternating estimation.

Datasets. For quantitative evaluation against ground-truth geometry, we generated a synthetic dataset consisting of 5 distinct sequences, each 29 frames in length. These sequences feature 5 different moving objects within 3 varied environments. Each sequence provides four-view videos with corresponding ground-truth 3D meshes. We further evaluate our method on two real world datasets capturing diverse human-object interactions: the HODome dataset [47] (high-fidelity capture of human-object interaction) and the HO3D dataset [14] (hand-object interaction focused on object pose estimation).

Baseline Methods. We evaluate the effectiveness of our method by comparing it with its ablated variants. “Single-Frame” is our initialization process and recovers geometry and appearance from only the initial timestep frames similar to MAtCha [13]. “w/o Motion-Aware Appearance” skips the optimization of geometry and appearance with the proposed appearance model. “w/o Alternating Estimation” skips the pose estimation and optimizes all the parameters from the beginning of the estimation at each timestep. For more detailed analysis on the appearance model, we also compare our method with “w/o Specular” and “w/o Diffuse” which ablate the specular and diffuse terms in Eq. (13), respectively. Note that for “w/o Diffuse”, we still use 0th order SH coefficients, which represents view- and motion-invariant color to let the gaussians have individual color.

Evaluation Metrics. To assess the quality of the recovered surface details, we compute the angular error between normal maps rendered from the Gaussians

Table 2: Novel view synthesis accuracy on synthetic data. The results high-
light that our proposed appearance model is essential for accurately recovering object
appearance from sparse multi-view observations.

Table 3: Surface mesh reconstruction on synthetic data. We evaluate geometric
accuracy using Chamfer Distance (CD, ↓) and Normal Error (↓). The results demonstrate
the superior precision of our reconstruction compared to baseline methods.

and the ground truth. We report the mean, median, and 80th percentile errors. Novel view synthesis accuracy is measured using PSNR, L1 error, SSIM, and LPIPS, calculated exclusively within the object regions. For the reconstructed mesh, we evaluate geometric fidelity using the Chamfer Distance (CD) and the average angular error of the surface normals. To calculate the latter, we compare the normal of each sampled point on the extracted mesh surface with the normal of the nearest point on the ground-truth surface.

### Evaluation on Synthetic Data

We first quantitatively evaluate our method using synthetic data with groundtruth surface details. Tables 1 to 3 summarize the accuracy of the recovered surface normals, novel view synthesis, and 3D mesh models. These results demonstrate

Fig. 4: Visualization of recovered surface normals. The error maps on the
right visualize per-pixel estimation discrepancies. These results demonstrate that proper
appearance modeling is essential for effectively leveraging radiometric cues to reconstruct
fine surface details.

Fig. 5: Novel view Synthesis. Our appearance model significantly improves the
fidelity of novel view synthesis when applied to objects with specularity.

that our proposed components are essential for reconstructing detailed geometry and appearance. Notably, our method achieves significantly higher accuracy than the single-frame baselines in surface normal estimation and novel view synthesis for the bunny and drill sequences, which feature complex geometries that pose a challenge for the baseline. Qualitative results for recovered surface normals and novel view synthesis are shown in Figs. 4 and 5. Without effectively leveraging radiometric cues, learned priors and cross-view photometric consistency provide insufficient information to resolve fine surface details. Consequently, the “w/o Motion-Aware Appearance” baseline recovers only coarse geometry and appearance. In contrast, our method successfully reconstructs accurate surface details and novel views by fully exploiting radiometric cues through the proposed appearance model. In Tabs. 1 to 3, we compare our method with DG-Mesh [21], a representative baseline for surface mesh recovery from multi-view RGB video. While DG-Mesh

Fig. 6: Surface normals and mesh models recovered from real-world datasets.
Qualitative results on HO3D [14] and HODome [47] demonstrate the effectiveness and
robustness of our method across diverse human-object interaction scenarios.

Views
Mesh

Fig. 7: Visualization of alternating estimation progress. We show the recovered
geometry and object poses (represented as effective camera views) at several timesteps.
As the temporal window expands and the effective camera coverage becomes more
informative, the geometric accuracy of the reconstruction progressively improves.

supports deformable objects, it requires extensive camera motion to jointly estimate geometry, appearance, and deformation. Consequently, it struggles with the sparse inputs provided by static cameras. In contrast, our method effectively leverages sparse, static-view observations by jointly optimizing object pose, geometry, and appearance. Note that we only report results of DG-Mesh [21] on the synthetic data as it did not produce meaningful results on real data due to occlusions from human subjects and large motions.

### Evaluation on Real-World Data

We further evaluate our method on several real-world datasets. To maintain our assumption of a single rigidly moving object, we pre-process the scenes to remove human subjects from the representation. During initialization, we exclude Gaussians projected onto annotated human segmentation masks; during multi-frame optimization, we mask human regions when computing loss functions. Figure 6 and Tab. 4 present qualitative and quantitative results for surface normals, 3D mesh models, and novel view synthesis. While these datasets provide

Table 4: Quantitative results on real-world datasets. Our method achieves better
geometry accuracy and novel view synthesis quality than the baselines.

ground-truth meshes, they often lack fine geometric details; therefore, we restrict our geometric evaluation to the Chamfer Distance (CD). Although real-world conditions may not strictly adhere to all model assumptions, our alternating estimation framework and appearance model consistently improve reconstruction quality, demonstrating the robustness of our approach. Figure 7 visualizes the recovered 3D shapes and object poses at several timesteps of the alternating optimization process. We represent object poses as “effective camera views”—the camera’s position relative to the object’s local coordinate system. The results confirm that our method successfully leverages object motion, progressively improving geometric accuracy as the diversity of effective viewpoints increases.

## Conclusion

We introduced a method to recover the 3D shape, appearance, and time-varying poses of a rigidly moving object from static, sparse-view RGB videos. By introducing an alternating estimation framework that leverages opportunistic motion and a dedicated model for complex view and pose-dependent appearance, our method successfully reconstructs detailed geometry and appearance from limited viewpoints. We believe this approach serves as a practical tool for 3D scene understanding in real-world scenarios, such as home safety monitoring for the elderly or children. Despite its effectiveness in handling sparse observations and dynamic appearance, certain limitations remain. First, because our method initializes canonical Gaussians using learned priors, it may fail on uncommon objects not represented in the training data. Second, our model assumes a simplified surface reflection model—comprising Lambertian and uniform, reflection-centered specular components—and distant illumination. Consequently, it may struggle with complex effects such as Fresnel reflection, microfacet-based light transport, or near-field lighting. Factorizing the specular component to disentangle the illumination for relighting represents another promising research direction. Finally, our framework assumes rigid bodies and does not currently handle deformable components. We plan to address these challenges in future work by using our current estimation framework as a foundation for more sophisticated modeling.

Acknowledgement

This work was in part supported by JSPS KAKENHI 21H04893, JST JPM- JAP2305, and the European Union (ERC Advanced Grant explorer Funding ID \#101097259) .

## References

1. Akio, D., Akio, K.: An Efficient Method of Triangulating Equi-Valued Surfaces by
Using Tetrahedral Cells. ACM Transactions on Graphics (1991) 9

2. Barron, J.T.: Mip-NeRF: A Multiscale Representation for Anti-Aliasing Neural
Radiance Fields. In: International Conference on Computer Vision (2021) 3

3. Barron, J.T.: Zip-NeRF: Anti-Aliased Grid-Based Neural Radiance Fields. In:
International Conference on Computer Vision (2023) 3

4. Cai, W., Ye, W., Ye, P., He, T., Chen, T.: DynaSurfGS: Dynamic Surface Recon-
struction with Planar-Based Gaussian Splatting. arXiv Preprint (2024) 3

5. Chen, A., Xu, Z., Geiger, A., Yu, J., Su, H.: TensoRF: Tensorial Radiance Fields.
In: European Conference on Computer Vision (2022) 3

6. Chen, Y., Chang, J., Ye, C., Zhang, C., Fang, Z., Li, C., Han, X.: ForeHOI: Feed-
Forward 3D Object Reconstruction from Daily Hand-Object Interaction Videos.
arXiv Preprint (2026) 4

7. Dai, P., Xu, J., Xie, W., Liu, X., Wang, H., Xu, W.: High-Quality Surface Recon-
struction Using Gaussian Surfels. In: ACM SIGGRAPH (2024) 3

8. Duisterhof, B.P., Zust, L., Weinzaepfel, P., Leroy, V., Cabon, Y., Revaud, J.:
MASt3R-SfM: a Fully-Integrated Solution for Unconstrained Structure-from-Motion.
In: International Conference on 3D Vision (2025) 6, 7

9. Fan, C.D., Chang, C.W., Liu, Y.R., Lee, J.Y., Huang, J.L., Tseng, Y.C., Liu, Y.L.:
SpectroMotion: Dynamic 3D Reconstruction of Specular Scenes. In: Conference on
Computer Vision and Pattern Recognition. pp. 21328–21338 (2025) 4

10. Gao, J., Gu, C., Lin, Y., Li, Z., Zhu, H., Cao, X., Zhang, L., Yao, Y.: Relightable
3D Gaussians: Realistic Point Cloud Relighting with Brdf Decomposition and Ray
Tracing. In: European Conference on Computer Vision. pp. 73–89 (2024) 4

11. Ge, W., Hu, T., Zhao, H., Liu, S., Chen, Y.C.: Ref-Neus: Ambiguity-Reduced
Neural Implicit Surface Learning for Multi-View Reconstruction with Reflection.
In: International Conference on Computer Vision. pp. 4251–4260 (2023) 4

12. Guédon, A., Gomez, D., Maruani, N., Gong, B., Drettakis, G., Ovsjanikov, M.:
MILo: Mesh-In-the-Loop Gaussian Splatting for Detailed and Efficient Surface
Reconstruction. ACM Transactions on Graphics (2025) 3, 9

13. Guédon, A., Ichikawa, T., Yamashita, K., Nishino, K.: MAtCha Gaussians: Atlas
of Charts for High-Quality Geometry and Photorealism from Sparse Views. In:
Conference on Computer Vision and Pattern Recognition (2025) 2, 3, 6, 7, 10, 18

14. Hampali, S., Rad, M., Oberweger, M., Lepetit, V.: HOnnotate: A Method for 3D
Annotation of Hand and Object Poses. In: Conference on Computer Vision and
Pattern Recognition (2020) 10, 13, 20

15. Huang, B., Yu, Z., Chen, A., Geiger, A., Gao, S.: 2D Gaussian Splatting for
Geometrically Accurate Radiance Fields. In: ACM SIGGRAPH (2024) 3, 4, 7, 18

16. Jiang, S., Ye, Q., Xie, R., Huo, Y., Chen, J.: Hand-Held Object Reconstruction
from RGB Video with Dynamic Interaction. In: Conference on Computer Vision
and Pattern Recognition. pp. 12220–12230 (2025) 4

17. Jiang, Y., Tu, J., Liu, Y., Gao, X., Long, X., Wang, W., Ma, Y.: Gaussianshader: 3D
Gaussian Splatting with Shading Functions for Reflective Surfaces. In: Conference
on Computer Vision and Pattern Recognition. pp. 5322–5332 (2024) 4

18. Jin, Y., Prasad, V., Jauhri, S., Franzius, M., Chalvatzaki, G.: 6DOPE-GS: Online
6D Object Pose Estimation Using Gaussian Splatting. In: International Conference
on Computer Vision (2025) 3

19. Kerbl, B., Kopanas, G., Leimkühler, T., Drettakis, G.: 3D Gaussian Splatting for
Real-Time Radiance Field Rendering. ACM Transactions on Graphics (2023) 2, 3,
7, 19

20. Kouros, G., Wu, M., Tuytelaars, T.: RGS-DR: Deferred Reflections and Residual
Shading in 2D Gaussian Splatting. In: International Conference on 3D Vision (2026)

21. Liu, I., Su, H., Wang, X.: Dynamic Gaussians Mesh: Consistent Mesh Reconstruction
from Dynamic Scenes. In: International Conference for Learning Representations
(2025) 3, 10, 11, 12, 13, 21, 23

22. Liu, X., Zhang, Q., Huang, X., Feng, Y., Zhou, G., Wang, Q.: H 2 O-NeRF: Ra-
diance Fields Reconstruction for Two-Hand-Held Objects. IEEE Transactions on
Visualization and Computer Graphics (2025) 4

23. Liu, Y., Wang, P., Lin, C., Long, X., Wang, J., Liu, L., Komura, T., Wang, W.:
NeRO: Neural Geometry and BRDF Reconstruction of Reflective Objects from
Multiview Images. ACM Transactions on Graphics (2023) 4

24. Long, X., Lin, C., Wang, P., Komura, T., Wang, W.: Sparseneus: Fast Generalizable
Neural Surface Reconstruction from Sparse Views. In: European Conference on
Computer Vision. pp. 210–227 (2022) 3

25. Mildenhall, B., Srinivasan, P.P., Tancik, M., Barron, J.T., Ramamoorthi, R., Ng,
R.: NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis. In:
European Conference on Computer Vision (2020) 3

26. Müller, T., Evans, A., Schied, C., Keller, A.: Instant Neural Graphics Primitives
with a Multiresolution Hash Encoding. ACM Transactions on Graphics (2022) 3

27. Ni, J., Chen, Y., Yang, Z., Liu, Y., Lu, R., Zhu, S.C., Huang, S.: G4Splat: Geometry-
Guided Gaussian Splatting with Generative Prior. In: International Conference for
Learning Representations (2026) 3

28. Park, K., Sinha, U., Barron, J.T., Bouaziz, S., Goldman, D.B., Seitz, S.M., Martin-
Brualla, R.: Nerfies: Deformable Neural Radiance Fields. In: International Confer-
ence on Computer Vision (2021) 3

29. Phong, B.T.: Illumination for Computer Generated Pictures. Commun. ACM 18(6),
311–317 (1975) 8

30. Pumarola, A., Corona, E., Pons-Moll, G., Moreno-Noguer, F.: D-NeRF: Neural
Radiance Fields for Dynamic Scenes. In: Conference on Computer Vision and
Pattern Recognition (2020) 3

31. Raj, K., Wewer, C., Yunus, R., Ilg, E., Lenssen, J.E.: Spurfies: Sparse-View Surface
Reconstruction Using Local Geometry Priors. In: International Conference on 3D
Vision (2025) 3

32. Ravi, N., Gabeur, V., Hu, Y.T., Hu, R., Ryali, C., Ma, T., Khedr, H., Rädle, R.,
Rolland, C., Gustafson, L., Mintun, E., Pan, J., Alwala, K.V., Carion, N., Wu, C.Y.,
Girshick, R., Dollar, P., Feichtenhofer, C.: SAM 2: Segment Anything in Images
and Videos. In: International Conference for Learning Representations (2025) 6, 19

33. Ren, Y., Wang, F., Zhang, T., Pollefeys, M., Süsstrunk, S.: Volrecon: Volume
Rendering of Signed Ray Distance Functions for Generalizable Multi-View Re-
construction. In: Conference on Computer Vision and Pattern Recognition. pp.
16685–16695 (2023) 3

34. Sara Fridovich-Keil and Alex Yu and Matthew Tancik and Qinhong Chen and
Benjamin Recht and Angjoo Kanazawa: Plenoxels: Radiance Fields Without Neural
Networks. In: Conference on Computer Vision and Pattern Recognition (2022) 3

35. Verbin, D., Hedman, P.: Ref-NeRF: Structured View-Dependent Appearance for
Neural Radiance Fields. In: Conference on Computer Vision and Pattern Recognition
(2022) 4

36. Wang, P., Liu, L., Liu, Y., Theobalt, C., Komura, T., Wang, W.: NeuS: Learning
Neural Implicit Surfaces by Volume Rendering for Multi-View Reconstruction. In:
Advances in Neural Information Processing Systems (2021) 3

37. Wang, W., Gleize, P., Tang, H., Chen, X., Liang, K.J., Feiszli, M.: Icon: Incremental
Confidence for Joint Pose and Radiance Field Optimization. In: Conference on
Computer Vision and Pattern Recognition. pp. 5406–5417 (2024) 4

38. Wang, Y., Han, Q., Habermann, M., Daniilidis, K., Theobalt, C., Liu, L.: NeuS2:
Fast Learning of Neural Implicit Surfaces for Multi-View Reconstruction. In: Inter-
national Conference on Computer Vision (2023) 3

39. Wen, B., Tremblay, J., Blukis, V., Tyree, S., Müller, T., Evans, A., Fox, D., Kautz,
J., Birchfield, S.: BundleSDF: Neural 6-DoF Tracking and 3D Reconstruction of
Unknown Objects. In: Conference on Computer Vision and Pattern Recognition
(2023) 3

40. Wu, H., Graikos, A., Samaras, D.: S-Volsdf: Sparse Multi-View Stereo Regularization
of Neural Implicit Surfaces. In: Conference on Computer Vision and Pattern
Recognition. pp. 3556–3568 (2023) 3

41. Yan, Z., Li, C., Lee, G.H.: NeRF-DS: Neural Radiance Fields for Dynamic Specular
Objects. In: Conference on Computer Vision and Pattern Recognition (2023) 4

42. Yang, L., Kang, B., Huang, Z., Zhao, Z., Xu, X., Feng, J., Zhao, H.: Depth Anything
V2. In: Advances in Neural Information Processing Systems (2024) 6, 7

43. Yang, Z., Gao, X., Zhou, W., Jiao, S., Zhang, Y., Jin, X.: Deformable 3D Gaussians
for High-Fidelity Monocular Dynamic Scene Reconstruction. In: Conference on
Computer Vision and Pattern Recognition (2024) 3

44. Yu, Z., Chen, A., Huang, B., Sattler, T., Geiger, A.: Mip-Splatting: Alias-Free 3D
Gaussian Splatting. In: Conference on Computer Vision and Pattern Recognition
(2024) 3

45. Yu, Z., Sattler, T., Geiger, A.: Gaussian Opacity Fields: Efficient Adaptive Surface
Reconstruction in Unbounded Scenes. ACM Transactions on Graphics (2024) 3

46. Yuan, W., Lv, Z., Schmidt, T., Lovegrove, S.: Star: Self-Supervised Tracking and
Reconstruction of Rigid Objects in Motion with Neural Rendering. In: Conference
on Computer Vision and Pattern Recognition. pp. 13144–13152 (2021) 4

47. Zhang, J., Luo, H., Yang, H., Xu, X., Wu, Q., Shi, Y., Yu, J., Xu, L., Wang, J.:
NeuralDome: A Neural Modeling Pipeline on Multi-View Human-Object Interac-
tions. In: Conference on Computer Vision and Pattern Recognition (2023) 10, 13,

48. Zhang, S., Wu, G., Xie, Z., Wang, X., Feng, B., Liu, W.: Dynamic 2D Gaussians:
Geometrically Accurate Radiance Fields for Dynamic Objects. In: ACM Multimedia
(2025) 3

49. Zhang, Y., Chen, A., Wan, Y., Song, Z., Yu, J., Luo, Y., Yang, W.: Ref-GS:
Directional Factorization for 2D Gaussian Splatting. In: Conference on Computer
Vision and Pattern Recognition (2025) 4

Fig. 8: Results on in-the-wild capture. Our method reconstructs faithful appearance
and geometry from real-world capture, including specular highlight on the object.

## Results on In-the-wild Capture

In Fig. 8 and the supplementary video, we test our method on in-the-wild videos captured by ourselves. We place cameras at the four corners of a room and record human–object interactions. To obtain ground-truth geometry, we also scan each object using a 3D scanner. Our method reconstructs accurate object geometry and appearance including specular highlight on the object even from these in-the-wild videos. The results show promise for great applicability of our method to real-world scenarios such as home safety monitoring for elderly people or children.

## Implementation Details

The learnable parameters of our method are the parameters of 2D Gaussians, the appearance parameters shared across the object (θ s and θ d), and per-frame object poses (quaternion q t obj and translation t t obj for each timestep). The parameters of each Gaussian are its 3D position µ i, rotation (quaternion) q i, 2D scale s i, opacity σ i, segmentation mask value m i, and diffuse albedo k d,i. During singleview 3D reconstruction and alternating estimation, we optimize a single set of SH coefficients θ i for each Gaussian instead of k d,i, θ s, and θ d. The sets of SH coeeficients θ s, θ d, and θ i correspond to spherical harmonics of orders 9, 3, and 3, respectively. We use the Adam optimizer for all the training stages.

Meshing For each Gaussian, we place pivot points at its center µ i and at the eight vertices of a cuboid aligned with the Gaussian orientation q i. The side lengths of the cuboid are set to three times the Gaussian scale s i. Along the surface normal direction, we use a fixed length of 2 × 10−4. For each pivot point, we use an SDF value computed by TSDF fusion as an initial value for the optimization. This post-processing takes approximately 10 minutes.

## Dataset Details

### Synthetic Dataset

The synthetic dataset consists of multi-view videos of five object-environment pairs drawn from five objects and three surrounding environments, namely, a drain cleaner in a room, an ottoman in a room, a bunny on a table in a room, a garden gnome on a table in a room, and a drill on a table in an airport. In the room environment, the scene consists of 3D models of furnitures, walls, and a floor illuminated by point light sources, whereas the other environments are composed of several 3D furniture models and an environment map. In each sequence, the object rotates in place while the surrounding environment remains static. The rotation between adjacent frames is 12.9 degrees. Four training viewpoints are placed around the object (corresponding to the four corners of the room in the room environment), and three intermediate viewpoints between them are used as test views for novel view synthesis. All images are rendered using Blender Cycles, producing photorealistic renderings with global illumination and surface roughness effects.

### HO3D Dataset [14]

For the HO3D dataset (a hand-object interaction dataset), we use the sequences that provide multi-view images, namely AP1, GPMF1, MDF1, and SB1. These sequences contain a variety of objects such as a pitcher, a bleach cleaner bottle, and a potted meat can. Among the five available camera views, we use four views surrounding the object as training views and use one remaining view for novel view synthesis evaluation. Since the object motion in HO3D is relatively slow, we subsample the input video by taking every 5th to 15th frame so that the total number of frames becomes approximately 100 and use the resulting frame sequence as input to our method.

### HODome Dataset [47]

For the HODome dataset (high-fidelity capture of human-object interaction), we use the box, chair, desk, table, talltable, trashcan, and trolleycase sequences, which cover a diverse set of objects. We select four views surrounding the object as training views and seven views from the remaining views for novel view synthesis evaluation. Since the sequences are temporally dense (60 FPS), we subsample them so that the total number of frames becomes around 50 before feeding them into our method. Note that we use only 33 frames for talltable sequence since the motion is relatively subtle.

## Additional Experimental Results

### Additional Qualitative Results on Synthetic Data

Figure 9 shows additional qualitative results of the surface normals recovered from
the synthetic dataset. The drain cleaner has relatively simple geometry and can

Fig. 9: Additional Visualization of Recovered Surface Normals. Our recovered
surface normals are at least comparable to those of the baselines, suggesting the
robustness of our method.

be handled well by the baseline methods, leaving limited room for improvement by our method. Nevertheless, our method achieves surface-normal estimates comparable to the baselines even on such an object, indicating robustness across different object complexities. Figure 10 shows additional novel view synthesis results on the synthetic dataset. Our appearance model improves the fidelity of novel view synthesis across different objects. The ottoman (the second row) remains challenging even for our method, as it exhibits limited surface-normal variation, providing only sparse view-dependent appearance observations for appearance recovery. Figure 11 shows a qualitative comparison with DG-Mesh [21]. While it supports deformable objects, it struggles to recover fine surface details from sparse inputs captured by static cameras.

### Effectiveness of Motion-Aware Appearance Modeling

Figures 12 and 13 show qualitative results of the ablation studies on the diffuse and specular components of our motion-aware appearance model. Removing either component degrades the recovery of view- and motion-dependent effects, leading to less faithful novel view synthesis and reduced surface-normal quality on objects with challenging materials such as the bunny. Figure 14 shows visualizations of the estimated specular and diffuse components. These results indicate that our method can effectively decompose the object appearance into specular highlights and diffuse shading, enabling separate analysis of each component. We further validate our motion-aware appearance model by comparing it against per-Gaussian SH, a variant of our method that optimizes spherical harmonics (SH) coefficients independently for each Gaussian, similar to 3D

Novel View

Fig. 10: Additional Novel View Synthesis Results. Our appearance model im-
proves the fidelity of novel view synthesis on different objects. The ottoman (the second
row) remains challenging due to its limited surface-normal variation.

Gaussian Splatting (3DGS). Table 5 and Fig. 15 show quantitative and qualitative results. Optimizing per-Gaussian SH coefficients can be unstable on complex objects such as the bunny, leading to degraded surface-normal and novel-view synthesis accuracy. In contrast, our full method with shared SH coefficients successfully recovers high-frequency details of surface normals, demonstrating the advantage of the shared SH coefficients.

### Effectiveness of Alternating Estimation

To further evaluate the effectiveness of our alternating estimation framework, we test our method under more challenging temporally sparse settings. Specifically, we construct subsampled videos by skipping every other frame and every two frames. In these settings, the object rotates by approximately 26 degrees and 39 degrees, respectively, between adjacent frames. Figure 16 shows qualitative comparisons between our full method and a variant without alternating estimation (“w/o Alternating Estimation”). Without alternating estimation, the joint estimation suffers from the strong interdependency between geometry, pose, and appearance. In contrast, our method successfully recovers geometry and appearance even from the sparsest videos, clearly demonstrating the effectiveness of the alternating estimation framework.

Fig. 11: Qualitative comparison with DG-Mesh [21]. While DG-Mesh supports
deformable objects, it struggles with the sparse inputs provided by static cameras.

### Effectiveness of Segmentation Mask Refinement

We also evaluate the effectiveness of refining the per-Gaussian segmentation mask values m i. We compare our method with w/o Segmentation Mask Refinement, a variant in which the mask values are fixed to their initial estimates throughout optimization. Figure 17 shows qualitative results. Mask refinement is essential for converging to the true fine-scale geometry.

### Additional Qualitative Results on Real-World Datasets

Figure 18 shows additional qualitative results of the reconstructed surface geom-
etry on real-world datasets. Our method recovers fine-grained geometric details
across objects with diverse shapes and material properties.

Fig. 12: Effectiveness of diffuse and specular components for surface normal
recovery. Modeling both diffuse and specular components is critical for recovering
accurate surface normals on objects with diverse material properties, where view-
dependent effects can otherwise bias the reconstruction.

Novel View

Fig. 13: Effectiveness of diffuse and specular components for novel view
synthesis. Our full model can faithfully reproduce both specular highlights and diffuse
shading.

Novel View

GT
Specular
Diffuse
Full

Fig. 14: Visualization of specular and diffuse components. In the second column
of the specular components, we show the results with increased brightness for better
visibility. Our method successfully decomposes the object appearance into specular and
diffuse components, except for the challenging case of the ottoman.

Table 5: Comparison with per-Gaussian SH, a variant of our method that
optimizes SH coefficients independently for each Gaussian. We report (a) surface
normal accuracy and (b) novel view synthesis quality on synthetic data. Optimizing
per-Gaussian SH can be unstable on complex objects (e.g., the bunny), leading to
degraded performance.

(a) Surface normal accuracy. Mean/median/80th percentile angular error (↓).

Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓ Mean ↓ Med. ↓ P80 ↓

(b) Novel view synthesis accuracy. PSNR/SSIM (↑), L1/LPIPS (↓).

PSNR ↑
SSIM ↑ LPIPS ↓

PSNR ↑
SSIM ↑ LPIPS ↓

Fig. 15: Qualitative comparison with per-Gaussian SH. In particular, our full
model yields sharper reconstructions of fine surface details (e.g., the wrinkles on the
bunny).

Appearance
Normal
Normal Error

Fig. 16: Comparison with our method without alternating estimation (“w/o
Alternating Estimation”). In the “10 frames,” “15 frames,” and “29 frames” settings,
the object rotates by approximately 39, 26, and 13 degrees, respectively, between
adjacent frames. Our full method successfully recovers geometry and appearance even
in the temporally sparsest setting.

Fig. 17: Effectiveness of segmentation mask refinement. We compare our full
method with a variant without mask refinement (“w/o Mask Refinement”), where the
per-Gaussian mask values are fixed during optimization. Refining the mask values
jointly with geometry and appearance is essential for converging to the true fine-scale
geometry.

Single Frame
Ours
GT

Fig. 18: Surface normals and mesh models recovered from real-world datasets.
The results demonstrate the effectiveness and robustness of our method across diverse
human-object interaction scenarios.
