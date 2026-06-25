# This shell script is to be sourced and run from a github workflow
# when xtgeoviz is to be tested towards a new RMS Python environment

run_tests() {
    set_test_variables

    copy_test_files

    install_test_dependencies

    run_pytest
}

set_test_variables() {
    echo "Setting variables for xtgeoviz tests..."
    CI_TEST_ROOT=$CI_ROOT/xtgeoviz_test_root
}

copy_test_files () {
    echo "Copy xtgeoviz test files to $CI_TEST_ROOT..."
    mkdir -p $CI_TEST_ROOT
    ln -s $XTGEO_TESTDATA_PATH $CI_ROOT/xtgeo-testdata
    cp -r $PROJECT_ROOT/tests $CI_TEST_ROOT

    echo "Create symlinks from $CI_TEST_ROOT to files in $PROJECT_ROOT..."
    ln -s $PROJECT_ROOT/conftest.py $CI_TEST_ROOT/conftest.py
    ln -s $PROJECT_ROOT/pyproject.toml $CI_TEST_ROOT/pyproject.toml
}

install_test_dependencies () {
    echo "Installing test dependencies..."
    pip install ".[tests]"

    echo "Dependencies installed successfully. Listing installed dependencies..."
    pip list
}

run_pytest () {
    echo "Running xtgeoviz tests with pytest..."
    pushd $CI_TEST_ROOT
    pytest ./tests -n 4 -vv --testdatapath $XTGEO_TESTDATA_PATH
    popd
}
