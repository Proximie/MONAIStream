#! /bin/bash

homedir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d $homedir/endoscopic_tool_segmentation ]
then
    python -m monai.bundle download --name endoscopic_tool_segmentation --bundle_dir $homedir
fi

cp $homedir/endoscopic_tool_segmentation_stream.json $homedir/endoscopic_tool_segmentation/configs/stream.json
