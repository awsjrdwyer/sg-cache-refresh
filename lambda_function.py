import boto3
import json

def lambda_handler(event, context):
    # Extract S3 bucket name from event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    
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
            
            # Filter file shares by S3 bucket name
            matching_shares = [
                share for share in file_shares 
                if share.get('LocationARN', '').endswith(f'/{bucket_name}')
            ]
            
            # Refresh cache for each matching file share
            for share in matching_shares:
                file_share_arn = share['FileShareARN']
                
                sg_client.refresh_cache(FileShareARN=file_share_arn)
                
                refresh_results.append({
                    'FileShareARN': file_share_arn,
                    'Region': region,
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
