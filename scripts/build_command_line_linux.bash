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

pyinstaller --onefile --exclude-module PyQt5 --exclude-module PyQt4 \
            --hidden-import PIL.Jpeg2KImagePlugin \
            --hidden-import pkg_resources \
            --hidden-import PIL._imaging \
            --hidden-import configobj \
            --distpath $BUILD_DIR/Web2ExeLinux-CMD \
            -n web2exe-linux $PROJ_DIR/command_line.py

cp -rf $PROJ_DIR/files $BUILD_DIR/Web2ExeLinux-CMD/files

## Remove any unneeded files
rm -rf $BUILD_DIR/Web2ExeLinux-CMD/files/downloads/*
rm $BUILD_DIR/Web2ExeLinux-CMD/files/error.log \
   $BUILD_DIR/Web2ExeLinux-CMD/files/last_project_path.txt \
   $BUILD_DIR/Web2ExeLinux-CMD/files/recent_files.txt \
   $BUILD_DIR/Web2ExeLinux-CMD/files/compressors/upx-mac \
   $BUILD_DIR/Web2ExeLinux-CMD/files/compressors/upx-win.exe

################# Build GUI Version ###################

pyinstaller -F --exclude-module PyQt5 --exclude-module PyQt4 \
            --hidden-import PIL.Jpeg2KImagePlugin \
            --hidden-import configobj \
            --hidden-import PIL._imaging \
            --hidden-import pkg_resources \
            -n web2exe --distpath $BUILD_DIR/Web2ExeLinux $PROJ_DIR/main.py

## Copy the files directory over
cp -rf $PROJ_DIR/files $BUILD_DIR/Web2ExeLinux/files

## Remove any unneeded files
rm -rf $BUILD_DIR/Web2ExeLinux/files/downloads/*
rm $BUILD_DIR/Web2ExeLinux/files/error.log \
   $BUILD_DIR/Web2ExeLinux/files/last_project_path.txt \
   $BUILD_DIR/Web2ExeLinux/files/recent_files.txt \
   $BUILD_DIR/Web2ExeLinux/files/compressors/upx-mac \
   $BUILD_DIR/Web2ExeLinux/files/compressors/upx-win.exe


################# Zip and Upload to Github ###################

cd $BUILD_DIR

zip -r -9 Web2ExeLinux-CMD.zip Web2ExeLinux-CMD/*
zip -r -9 Web2ExeLinux-${VERSION}.zip Web2ExeLinux

cd -

python3.4 $DIR/upload_release.py
