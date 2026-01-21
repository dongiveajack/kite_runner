#!/bin/bash

# Configuration
PACKAGE_DIR="lambda_package"
ZIP_FILE="kite_lambda_deploy.zip"

echo "Cleaning up..."
rm -rf "$PACKAGE_DIR" "$ZIP_FILE"
mkdir "$PACKAGE_DIR"

echo "Installing dependencies (excluding locally compiled binaries)..."
# We exclude psycopg2-binary because we need to use a Lambda Layer for it
# Install requirements from dedicated lambda file (which excludes psycopg2)
# We use --ignore-installed to ensure we get fresh copies suitable for the package
pip install -r requirements_lambda.txt --target "$PACKAGE_DIR" --ignore-installed

# Aggressively remove psycopg2 artifacts using find
# This is critical because if local psycopg2 exists, it shadows the Lambda Layer and causes module import errors
echo "Removing local psycopg2 artifacts..."
find "$PACKAGE_DIR" -name "psycopg2*" -exec rm -rf {} +
find "$PACKAGE_DIR" -name "Psycopg2*" -exec rm -rf {} +

echo "Copying source code..."
cp -r src "$PACKAGE_DIR/"
cp main.py "$PACKAGE_DIR/"
cp lambda_function.py "$PACKAGE_DIR/"
# Copy .env file so environment variables are loaded automatically on Lambda
# START: Insecure but convenient for personal projects
if [ -f .env ]; then
    cp .env "$PACKAGE_DIR/"
    echo "Included .env file."
else
    echo "Warning: .env file not found!"
fi
# END: Insecure but convenient

echo "Creating Zip file..."
cd "$PACKAGE_DIR"
zip -r9 "../$ZIP_FILE" .
cd ..

echo "Deployment package created: $ZIP_FILE"
echo "Done."
