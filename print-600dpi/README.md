# 男女体表精绘与 600 DPI 输出

本轮按 **20–25 岁成年人（画稿设定 23 岁）** 重新绘制亚洲青年男女：6 张独立全身单视图，以及男女各 2 张分区精绘图。女性面容与眉眼精修，采用马尾和疏朗刘海；全身图使用不透明的无肩带胸部遮盖，后背不设背心或横向布带，短裤缩短并完整覆盖骨盆、臀部与大腿近端。三视图采用单视图原始像素拼版，不是将旧三视图整体放大。

## 查看与下载

| 内容 | 原生图像 | A3、600 DPI 输出 |
| --- | --- | --- |
| 男性全身三视图 | [PNG](native/male-three-views.png) · [原生像素 TIFF](native/male-three-views-native-600dpi.tif) | [PNG](A3-600dpi/male-three-views-A3-600dpi.png) |
| 女性全身三视图 | [PNG](native/female-three-views.png) · [原生像素 TIFF](native/female-three-views-native-600dpi.tif) | [PNG](A3-600dpi/female-three-views-A3-600dpi.png) |
| 男性头颈、肩背与上半身 | [PNG](sources/male-upper-detail.png) · [原生像素 TIFF](native/male-upper-detail-native-600dpi.tif) | [PNG](A3-600dpi/male-upper-detail-A3-600dpi.png) |
| 女性面部、头颈、锁骨与后肩 | [PNG](sources/female-upper-detail.png) · [原生像素 TIFF](native/female-upper-detail-native-600dpi.tif) | [PNG](A3-600dpi/female-upper-detail-A3-600dpi.png) |
| 男性下肢、膝踝与足部 | [PNG](sources/male-lower-detail.png) · [原生像素 TIFF](native/male-lower-detail-native-600dpi.tif) | [PNG](A3-600dpi/male-lower-detail-A3-600dpi.png) |
| 女性下肢、膝踝与足部 | [PNG](sources/female-lower-detail.png) · [原生像素 TIFF](native/female-lower-detail-native-600dpi.tif) | [PNG](A3-600dpi/female-lower-detail-A3-600dpi.png) |

`sources/` 还保留每个性别的 front、side、back 独立全身图。旧的 300 DPI 文件仍保留在仓库 `print/` 中。

## 像素、DPI 和实际尺寸

- 全身单视图：每张原生 **1024 × 1536** 像素。
- 全身三视图拼版：**3072 × 1616** 像素；其中顶部 80 像素是排版增加的视图标题，不是新的人体细节。相比旧版 1312 × 1199，总像素约为 3.15 倍。
- 头颈/上半身精绘：男女均为 **1659 × 948** 像素。女性正面和侧面采用头颈、锁骨近景裁幅，后面展示肩背；不包含正面胸部。
- 下肢精绘：男女均为 **1536 × 1024** 像素。
- A3 输出：**9921 × 7016** 像素、600 DPI、RGB、嵌入 sRGB ICC，约 10 mm 以上白边，等比例居中排版，不裁切或拉伸人体。

**A3、600 DPI 文件包含 Lanczos 插值，不是原生生成的 9921 × 7016 解剖细节。**本轮真实增加的信息来自独立单视图和区域重新绘制；不能仅凭 600 DPI 元数据判断出版质量。

`native/*-native-600dpi.tif` 保持原生像素不变，仅设置 600 DPI 并采用 LZW 无损压缩。全身三视图在原生 600 DPI 下对应约 **130.0 × 68.4 mm**；上半身精绘约 **70.2 × 40.1 mm**；下肢精绘约 **65.0 × 43.3 mm**。若放大到 A3，真实细节密度就低于 600 DPI。`validation.json` 记录了每个文件的像素、DPI、尺寸与校验值。

## 医学与使用边界

这些图参考原有亚洲成年男女外观，调整为成年青年设定并重新绘制完整视角和局部体表；属于 AI 医学插图候选稿，不是影像重建、真实人体扫描或配准的三维投影。各视图和精绘区域可能存在比例、肤色、衣物与局部结构差异，不宜据此跨视图测量，也不应将局部图拼回原图冒充严格配准结果。

已经人工查看人物是否完整、视角、主要衣物覆盖与整体体表表现，并验证文件参数。尚未经医学专家逐项解剖校核。正式出版仍需按实际尺寸打样，并由专业人员审校结构与标注；CMYK、PDF/X 和出血应按出版社要求另外制作。
