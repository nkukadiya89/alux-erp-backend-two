import os
from os import path, remove
from os.path import isfile
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from decouple import config
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from PIL import Image
from rest_framework import serializers

ACCESS_KEY = config("AWS_ACCESS_KEY", default=None)
SECRET_KEY = config("AWS_SECRET_KEY", default=None)
REGION_NAME = config("REGION_NAME", default=None)
BUCKET = config("BUCKET_NAME", default=None)


def get_bucket_file_folder(aws_file_url):
    o = urlparse(aws_file_url, allow_fragments=False)
    return o.path.lstrip("/")


def file_extention(file_path):
    return path.splitext(file_path)[1]


def upload_file_to_bucket(
    upload_file,
    allowed_type: list,
    folder_name: str,
    p_value: int,
    file_name=None,
    presigned_expiry=300,
):
    file_type = file_extention(str(upload_file))

    if file_type.lower() not in allowed_type:
        raise serializers.ValidationError("File Type not supported")

    if file_name is None:
        file_name = timezone.now().strftime("%Y%m%d_%H%M%S")

    if not all([ACCESS_KEY, SECRET_KEY, REGION_NAME, BUCKET]):
        # Store locally in MEDIA folder when AWS credentials are not available
        s3_file = f"{folder_name}" + str(p_value) + "_" + file_name + file_type
        local_path = os.path.join(settings.MEDIA_ROOT, "uploads", s3_file)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        file_to_upload = Image.open(upload_file)
        file_to_upload.save(local_path)

        file_size = os.path.getsize(local_path) / 1000
        if file_size > 5120:
            remove(local_path)
            raise serializers.ValidationError("File size too large")

        # Return full absolute URL that React can access
        relative_path = os.path.join("uploads", s3_file).replace(os.sep, "/")
        file_url = f"{settings.BASE_URL.rstrip('/')}{settings.MEDIA_URL}{relative_path}"
        return file_url, file_url

    s3 = boto3.client(
        "s3",
        region_name=REGION_NAME,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    file_to_upload = Image.open(upload_file)
    picture_format = "image/" + file_to_upload.format.lower()  # type: ignore

    tempfile = settings.MEDIA_ROOT + file_name + file_type
    file_to_upload.save(tempfile)

    s3_file = f"{folder_name}" + str(p_value) + "_" + file_name + file_type

    aws_file_url = f"http://{BUCKET}.s3.{REGION_NAME}.amazonaws.com/{s3_file}"
    file_size = os.path.getsize(tempfile) / 1000
    if file_size > 5120:
        remove(tempfile)
        raise serializers.ValidationError("File size too large")

    s3.upload_file(
        tempfile,
        BUCKET,
        s3_file,
        ExtraArgs={"ACL": "public-read", "ContentType": picture_format},
    )

    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": get_bucket_file_folder(aws_file_url)},
        ExpiresIn=presigned_expiry,
    )

    if isfile(tempfile):
        remove(tempfile)
    return aws_file_url, presigned_url


def upload_doc_file(
    upload_file,
    allowed_type: list,
    folder_name: str,
    p_value: int,
    file_name=None,
    presigned_expiry=300,
):
    file_type = file_extention(str(upload_file))

    if file_type.lower() not in allowed_type:
        raise serializers.ValidationError("File Type not supported")

    if file_name is None:
        file_name = timezone.now().strftime("%Y%m%d-%H%M%S")

    if not all([ACCESS_KEY, SECRET_KEY, REGION_NAME, BUCKET]):
        # Store locally in MEDIA folder when AWS credentials are not available
        s3_file = f"{folder_name}" + str(p_value) + "_" + file_name + file_type
        local_path = os.path.join(settings.MEDIA_ROOT, "uploads", s3_file)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, "wb") as f:
            f.write(upload_file.read())

        file_size = os.path.getsize(local_path) / 1000
        if file_size > 5120:
            remove(local_path)
            raise serializers.ValidationError("File size too large")

        # Return full absolute URL that React can access
        relative_path = os.path.join("uploads", s3_file).replace(os.sep, "/")
        file_url = f"{settings.BASE_URL.rstrip('/')}{settings.MEDIA_URL}{relative_path}"
        return file_url, file_url

    path = default_storage.save(
        "./" + upload_file.name, ContentFile(upload_file.read())
    )
    tempfile = os.path.join(settings.MEDIA_ROOT, path)

    s3 = boto3.client(
        "s3",
        region_name=REGION_NAME,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    s3_file = f"{folder_name}" + str(p_value) + "_" + file_name + file_type

    aws_file_url = f"https://{BUCKET}.s3.{REGION_NAME}.amazonaws.com/{s3_file}"

    file_size = os.path.getsize(tempfile) / 1000
    if file_size > 5120:
        remove(tempfile)
        raise serializers.ValidationError("File size too large")

    s3.upload_file(
        tempfile,
        BUCKET,
        s3_file,
        ExtraArgs={"ACL": "public-read"},
    )

    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": get_bucket_file_folder(aws_file_url)},
        ExpiresIn=presigned_expiry,
    )
    if isfile(tempfile):
        remove(tempfile)

    return aws_file_url, presigned_url


def delete_uploaded_file(uploaded_file):
    if uploaded_file:
        s3 = boto3.client(
            "s3",
            region_name=REGION_NAME,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
        )
        file_to_delete = get_bucket_file_folder(uploaded_file)
        if s3.list_objects_v2(Bucket=BUCKET, Prefix=file_to_delete)["KeyCount"] >= 1:
            s3.delete_object(Bucket=BUCKET, Key=file_to_delete)
            return True
        else:
            return False
    else:
        return True


def delete_uploaded_die_file(uploaded_file):
    if not uploaded_file:
        return True  # Nothing to delete

    # Check if it's a local file (starts with BASE_URL or MEDIA_URL)
    if uploaded_file.startswith(settings.BASE_URL) or uploaded_file.startswith(
        settings.MEDIA_URL
    ):
        # Extract relative path from full URL or relative URL
        if uploaded_file.startswith(settings.BASE_URL):
            # Full URL: https://devservices.aluxerp.com/media/uploads/...
            relative_path = uploaded_file.replace(settings.BASE_URL.rstrip("/"), "", 1)
            relative_path = relative_path.replace(settings.MEDIA_URL, "", 1)
        else:
            # Relative URL: /media/uploads/...
            relative_path = uploaded_file.replace(settings.MEDIA_URL, "", 1)

        local_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                return True
            except Exception as e:
                print(f"Error deleting local file: {e}")
                return False
        else:
            # File does not exist
            return False

    # Handle S3 deletion
    if not all([ACCESS_KEY, SECRET_KEY, REGION_NAME, BUCKET]):
        # No S3 credentials and not a local file
        return False

    s3 = boto3.client(
        "s3",
        region_name=REGION_NAME,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    file_to_delete = get_bucket_file_folder(uploaded_file)

    try:
        # Check if the file exists
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=file_to_delete)
        if "Contents" in response and len(response["Contents"]) > 0:
            # File exists, delete it
            s3.delete_object(Bucket=BUCKET, Key=file_to_delete)
            return True
        else:
            # File does not exist
            return False
    except ClientError as e:
        # Log specific AWS Client errors
        print(f"AWS ClientError: {e}")
        return False
    except Exception as e:
        # Log any unexpected errors
        print(f"Unexpected Error: {e}")
        return False


def delete_uploaded_bloster_file(uploaded_file):
    if not uploaded_file:
        return True  # Nothing to delete

    # Check if it's a local file (starts with BASE_URL or MEDIA_URL)
    if uploaded_file.startswith(settings.BASE_URL) or uploaded_file.startswith(
        settings.MEDIA_URL
    ):
        # Extract relative path from full URL or relative URL
        if uploaded_file.startswith(settings.BASE_URL):
            # Full URL: https://devservices.aluxerp.com/media/uploads/...
            relative_path = uploaded_file.replace(settings.BASE_URL.rstrip("/"), "", 1)
            relative_path = relative_path.replace(settings.MEDIA_URL, "", 1)
        else:
            # Relative URL: /media/uploads/...
            relative_path = uploaded_file.replace(settings.MEDIA_URL, "", 1)

        local_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                return True
            except Exception as e:
                print(f"Error deleting local file: {e}")
                return False
        else:
            # File does not exist
            return False

    # Handle S3 deletion
    if not all([ACCESS_KEY, SECRET_KEY, REGION_NAME, BUCKET]):
        # No S3 credentials and not a local file
        return False

    s3 = boto3.client(
        "s3",
        region_name=REGION_NAME,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    file_to_delete = get_bucket_file_folder(uploaded_file)

    try:
        # Check if the file exists
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=file_to_delete)
        if "Contents" in response and len(response["Contents"]) > 0:
            # File exists, delete it
            s3.delete_object(Bucket=BUCKET, Key=file_to_delete)
            return True
        else:
            # File does not exist
            return False
    except ClientError as e:
        # Log specific AWS Client errors
        print(f"AWS ClientError: {e}")
        return False
    except Exception as e:
        # Log any unexpected errors
        print(f"Unexpected Error: {e}")
        return False
