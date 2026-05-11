#!/bin/bash
set -e

DEST="/Volumes/Udisk2/ragent"
SRC="/Volumes/SSD1/ragent"

echo "开始拷贝未提交文件到U盘..."

# 1. 拷贝pytorch_model.bin (2.1G)
echo "拷贝 pytorch_model.bin..."
mkdir -p "$DEST/mep/model_packages/bge-m3/modelDir/model/"
cp "$SRC/mep/model_packages/bge-m3/modelDir/model/pytorch_model.bin" "$DEST/mep/model_packages/bge-m3/modelDir/model/"
echo "完成 pytorch_model.bin"

# 2. 拷贝 .mep_upload (4.4G)
echo "拷贝 .mep_upload..."
mkdir -p "$DEST/.mep_upload"
cp -r "$SRC/.mep_upload" "$DEST/"
echo "完成 .mep_upload"

# 3. 拷贝 .runtime (1.8G)
echo "拷贝 .runtime..."
mkdir -p "$DEST/.runtime"
cp -r "$SRC/.runtime" "$DEST/"
echo "完成 .runtime"

# 4. 拷贝 vendor (22G) - 最重要的离线部署包
echo "拷贝 vendor..."
mkdir -p "$DEST/vendor"
cp -r "$SRC/vendor" "$DEST/"
echo "完成 vendor"

# 5. 拷贝其他有用的忽略文件
echo "拷贝其他忽略文件..."
[ -f "$SRC/.env" ] && cp "$SRC/.env" "$DEST/"
[ -d "$SRC/.venv" ] && mkdir -p "$DEST/.venv" && cp -r "$SRC/.venv" "$DEST/"

echo "所有文件拷贝完成！"
du -sh "$DEST"
EOF
chmod +x /Volumes/SSD1/ragent/copy_to_udisk.sh
cat /Volumes/SSD1/ragent/copy_to_udisk.sh