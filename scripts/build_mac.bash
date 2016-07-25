DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

README=""
PROJ_DIR=$DIR

while [[ -z $README ]] && [[ $PROJ_DIR != "/" ]]; do
    README=$(find $PROJ_DIR -maxdepth 1 -name "README.md")

    if [[ -z $README ]]; then
        PROJ_DIR="$(dirname $PROJ_DIR)"
    fi
done

if [[ $PROJ_DIR == "/" ]]; then
    echo "No suitable project directory was found. Exiting."
    exit 1
fi

BUILD_DIR="$PROJ_DIR/Web2ExeBuild"

## Remove old build directories
rm -rf $PROJ_DIR/build $BUILD_DIR

VERSION=$(cat $PROJ_DIR/files/version.txt)

################# Build CMD Version ###################

pyinstaller --hidden-import PIL.Jpeg2KImagePlugin \
            --hidden-import configobj \
            --hidden-import pkg_resources \
            --distpath $BUILD_DIR/Web2ExeMac-CMD \
            --onefile -n web2exe-mac $PROJ_DIR/command_line.py

CMD_FILES_DIR=$BUILD_DIR/Web2ExeMac-CMD/files

cp -rf $PROJ_DIR/files $CMD_FILES_DIR

rm -rf $CMD_FILES_DIR/downloads/*
rm $CMD_FILES_DIR/error.log \
   $CMD_FILES_DIR/last_project_path.txt \
   $CMD_FILES_DIR/recent_files.txt \
   $CMD_FILES_DIR/compressors/upx-linux-x64 \
   $CMD_FILES_DIR/compressors/upx-linux-x32 \
   $CMD_FILES_DIR/compressors/upx-win.exe

rm -rf $PROJ_DIR/build $PROJ_DIR/dist

################# Build GUI Version ###################

pyinstaller -w --hidden-import PIL.Jpeg2KImagePlugin \
               --hidden-import PyQt4 \
               --hidden-import PIL \
               --hidden-import configobj \
               --hidden-import pkg_resources \
               --distpath $BUILD_DIR/ \
               --onefile -n Web2Executable $PROJ_DIR/main.py

FILES_DIR=$BUILD_DIR/Web2Executable.app/Contents/MacOS/files

cp $PROJ_DIR/images/icon.icns $BUILD_DIR/Web2Executable.app/Contents/Resources/icon-windowed.icns
cp -rf files $FILES_DIR

rm -rf $FILES_DIR/downloads/*
rm $FILES_DIR/error.log \
   $FILES_DIR/last_project_path.txt \
   $FILES_DIR/recent_files.txt \
   $FILES_DIR/compressors/upx-linux-x64 \
   $FILES_DIR/compressors/upx-linux-x32 \
   $FILES_DIR/compressors/upx-win.exe

rm -rf $PROJ_DIR/build $PROJ_DIR/dist

################# Zip and Upload to Github ###################

/Applications/Keka.app/Contents/Resources/keka7z a -r \
    Web2ExeMac-CMD.zip $BUILD_DIR/Web2ExeMac-CMD

/Applications/Keka.app/Contents/Resources/keka7z a -r \
    Web2ExeMac-${VERSION}.zip $BUILD_DIR/Web2Executable.app

python3.4 $DIR/upload_release.py
