import boto3
import json

def lambda_handler(event, context):
    # Extract S3 event details
    s3_record = event['Records'][0]
    bucket_name = s3_record['s3']['bucket']['name']
    object_key = s3_record['s3']['object']['key']
    
    # Exit only if it's a PUT and more than 1 version exists
    if s3_record['eventName'] == 'ObjectCreated:Put':
        s3_client = boto3.client('s3')
        versions = s3_client.list_object_versions(
            Bucket=bucket_name,
            Prefix=object_key
        )
        
        if len(versions.get('Versions', [])) > 1:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Skipped - more than 1 version exists'})
            }
    
    # Define regions to check
    regions = ['us-east-1', 'us-east-2']
    
    refresh_results = []
    
    try:
        for region in regions:
            # Initialize Storage Gateway client for each region
            sg_client = boto3.client('storagegateway', region_name=region)
            
            # List all file shares in this region
            response = sg_client.list_file_shares()
            file_shares = response['FileShareInfoList']
            
            # Check each file share for bucket match
            for share in file_shares:
                file_share_arn = share['FileShareARN']
                
                # Get detailed info including LocationARN
                describe_response = sg_client.describe_smb_file_shares(
                    FileShareARNList=[file_share_arn]
                )
                
                smb_file_share = describe_response['SMBFileShareInfoList'][0]
                location_arn = smb_file_share.get('LocationARN', '')
                
                # Check if bucket name is in the LocationARN
                if bucket_name in location_arn:
                    sg_client.refresh_cache(FileShareARN=file_share_arn)
                    
                    refresh_results.append({
                        'FileShareARN': file_share_arn,
                        'Region': region,
                        'LocationARN': location_arn,
                        'RefreshStatus': 'Success'
                    })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Cache refresh initiated for {len(refresh_results)} file shares',
                'bucket': bucket_name,
                'results': refresh_results
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'bucket': bucket_name
            })
        }
