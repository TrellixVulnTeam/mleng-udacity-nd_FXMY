import os
# os.system("pip install pandas")
# os.system("pip install sagemaker")
# os.system("pip install matplotlib")
import requests
import tarfile
import pandas as pd
import sagemaker
import boto3
import numpy as np
import pickle
import matplotlib.pyplot as plt
import boto3

def extract_cifar_data(url, filename="cifar.tar.gz"):
    """A function for extracting the CIFAR-100 dataset and storing it as a gzipped file
    
    Arguments:
    url      -- the URL where the dataset is hosted
    filename -- the full path where the dataset will be written
    
    """
    
   #Extract data from server
    r = requests.get(url)
    with open(filename, "wb") as file_context:
        file_context.write(r.content)
    return

def transform_data(filename = "cifar.tar.gz"):
    #Transform data from gzip into usefull format
    with tarfile.open(filename, "r:gz") as tar:
        tar.extractall()
        
    #Generate datasets for training and test
    with open("./cifar-100-python/meta", "rb") as f:
        dataset_meta = pickle.load(f, encoding='bytes')
    with open("./cifar-100-python/test", "rb") as f:
        dataset_test = pickle.load(f, encoding='bytes')
    with open("./cifar-100-python/train", "rb") as f:
        dataset_train = pickle.load(f, encoding='bytes')
        
    print('Downloading dataset {} with shape : {}'.format('meta',dataset_meta.keys()))
    print('Downloading dataset {} with shape : {}'.format('train',dataset_train.keys()))
    print('Downloading dataset {} with shape : {}'.format('meta',dataset_test.keys()))
    
    return dataset_meta,dataset_test,dataset_train

def get_train_test_dataframes(labels_to_filter,train,test,meta):
    try :
        labels = set([train[b'fine_labels'][n] for n in range(len(train[b'fine_labels'])) if meta[b'fine_label_names'][train[b'fine_labels'][n]] in labels_to_filter])
        print('Labels finded!\n{}'.format(dict(zip(labels_to_filter,labels))))
    except :
        print('Labels not finded! Please select valid figures')
    #Construct the dataframe
    df_train = pd.DataFrame({
        "filenames": train[b'filenames'],
        "labels": train[b'fine_labels'],
        "row": range(len(train[b'filenames']))
    })

    # Drop all rows from df_train where label is not the specified
    df_train = df_train[df_train['labels'].isin(list(labels))]

    # Decode df_train.filenames so they are regular strings
    df_train["filenames"] = df_train["filenames"].apply(
        lambda x: x.decode("utf-8")
    )
    df_test = pd.DataFrame({
        "filenames": test[b'filenames'],
        "labels": test[b'fine_labels'],
        "row": range(len(test[b'filenames']))
    })

    # Drop all rows from df_test where label is not the specified
    df_test = df_test[df_test['labels'].isin(list(labels))]

    # Decode df_test.filenames so they are regular strings
    df_test["filenames"] = df_test["filenames"].apply(
        lambda x: x.decode("utf-8")
    )
   
    return df_train,df_test

def save_images(filename,idx,dir_,df,df_meta):
    
    #Create temp directories for train and test data
    trainpath = r'./train/' 
    if not os.path.exists(trainpath):
        os.makedirs(trainpath)
    testpath = r'./test/' 
    if not os.path.exists(testpath):
        os.makedirs(testpath)
    
    #df = globals()['dataset_{}'.format(dir_)]
    path = './{}/{}'.format(dir_,filename)
    
    #Grab the image data in row-major form
    img = df[b'data'][idx]
    
    # Consolidated stacking/reshaping from earlier
    target = np.dstack((
        img[0:1024].reshape(32,32),
        img[1024:2048].reshape(32,32),
        img[2048:].reshape(32,32)
        ))
    
    # Save the image
    plt.imsave(path, target)
    
    # Return any signal data you want for debugging
    return print({filename : df_meta[b'fine_label_names'][df[b'fine_labels'][idx]]})

def send_to_s3(bucket,):
    session = sagemaker.Session()
    os.environ["DEFAULT_S3_BUCKET"] = bucket
    os.system("aws s3 sync ./train s3://${DEFAULT_S3_BUCKET}/train/")
    os.system("aws s3 sync ./test s3://${DEFAULT_S3_BUCKET}/test/")
    #!aws s3 sync ./train s3://${DEFAULT_S3_BUCKET}/train/
    #!aws s3 sync ./test s3://${DEFAULT_S3_BUCKET}/test/
    
    print("Default Bucket: {}".format(bucket))
    region = session.boto_region_name
    print("AWS Region: {}".format(region))
    role = sagemaker.get_execution_role()
    print("RoleArn: {}".format(role))
    
def to_metadata_file(df, prefix,bucket):
    #Create folder for metadata
    metadatapath = r'./metadata/' 
    if not os.path.exists(metadatapath):
        os.makedirs(metadatapath)
    df["s3_path"] = df["filenames"]
    df["labels"] = df["labels"].apply(lambda x: 0 if x==8 else 1)
    df[["row", "labels", "s3_path"]].to_csv(
        f"metadata/{prefix}.lst", sep="\t", index=False, header=False)
    # Upload files
    boto3.Session().resource('s3').Bucket(
        bucket).Object(f'{prefix}.lst').upload_file(f"./metadata/{prefix}.lst")

# labels_to_filter = [b'bicycle',b'motorcycle']
# bucket = 'project-scones-unlimited'

# #Extract data
# extract_cifar_data("https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz")     
# #Tranform extracted data
# dataset_meta,dataset_test,dataset_train = transform_data()
# #Get train and test data for informed labels
# df_train,df_test = get_train_test_dataframes(labels_to_filter,dataset_train,dataset_test,dataset_meta)
# #Extract images and save into train and test local directory
# df_train.apply(lambda x : save_images(x['filenames'],x['row'],'train'),axis=1)
# df_test.apply(lambda x : save_images(x['filenames'],x['row'],'test'),axis=1)
# #Send images to s3
# send_to_s3(bucket)
# #Sending matadata for training the image classifier model
# to_metadata_file(df_train.copy(), "train")
# to_metadata_file(df_test.copy(), "test")
