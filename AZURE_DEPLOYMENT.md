# Azure Deployment Guide for Hercule

This guide walks through deploying the Hercule backend to Azure Functions with Cosmos DB.

## Prerequisites

1. **Azure CLI** installed and logged in: `az login`
2. **Azure Functions Core Tools v4**: `npm install -g azure-functions-core-tools@4`
3. **Python 3.11+** installed
4. An **Azure subscription**

## Step 1: Create Azure Resources

### Option A: Using Azure Portal (Recommended for beginners)

1. **Create Resource Group**
   - Go to [Azure Portal](https://portal.azure.com)
   - Create a new Resource Group (e.g., `hercule-rg`)

2. **Create Cosmos DB Account**
   - Search for "Azure Cosmos DB" → Create
   - Choose "Azure Cosmos DB for NoSQL"
   - Name: `hercule-cosmos` (must be globally unique)
   - Region: Choose nearest to your users
   - Capacity: "Serverless" (cheaper for low traffic)
   
3. **Create Function App**
   - Search for "Function App" → Create
   - Name: `hercule-api` (must be globally unique)
   - Runtime: Python 3.11
   - Hosting: Consumption (Serverless)
   - Region: Same as Cosmos DB

### Option B: Using Azure CLI

```bash
# Set variables
RESOURCE_GROUP="hercule-rg"
LOCATION="eastus"
COSMOS_ACCOUNT="hercule-cosmos-$(date +%s)"
FUNCTION_APP="hercule-api-$(date +%s)"
STORAGE_ACCOUNT="herculestorage$(date +%s | cut -c1-8)"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Cosmos DB account (serverless)
az cosmosdb create \
  --name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --default-consistency-level Session \
  --capabilities EnableServerless

# Create Cosmos DB database and container
az cosmosdb sql database create \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --name "privacy-analyzer"

az cosmosdb sql container create \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --database-name "privacy-analyzer" \
  --name "analysis-cache" \
  --partition-key-path "/id"

# Create storage account (required for Functions)
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Create Function App
az functionapp create \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --storage-account $STORAGE_ACCOUNT \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux
```

## Step 2: Get Connection Strings

### Cosmos DB Connection String
```bash
# Using Azure CLI
az cosmosdb keys list \
  --name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" \
  --output tsv
```

Or from Portal: Cosmos DB → Settings → Keys → Primary Connection String

### Storage Account Connection String
```bash
az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString \
  --output tsv
```

## Step 3: Configure Environment Variables

Set these in Azure Portal: Function App → Configuration → Application settings

| Setting | Value |
|---------|-------|
| `GROQ_API_KEY` | Your Groq API key from console.groq.com |
| `STORAGE_MODE` | `cosmos` |
| `COSMOS_CONNECTION_STRING` | From Step 2 |
| `COSMOS_DATABASE_NAME` | `privacy-analyzer` |
| `COSMOS_CONTAINER_NAME` | `analysis-cache` |
| `ALLOWED_ORIGINS` | `*` (or specific origins) |

Or using CLI:
```bash
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    "GROQ_API_KEY=gsk_your_key_here" \
    "STORAGE_MODE=cosmos" \
    "COSMOS_CONNECTION_STRING=AccountEndpoint=..." \
    "COSMOS_DATABASE_NAME=privacy-analyzer" \
    "COSMOS_CONTAINER_NAME=analysis-cache" \
    "ALLOWED_ORIGINS=*"
```

## Step 4: Deploy the Backend

```bash
# Navigate to backend directory
cd backend

# Install dependencies locally first (optional, for testing)
pip install -r requirements.txt

# Deploy to Azure
func azure functionapp publish <your-function-app-name>
```

Example:
```bash
func azure functionapp publish hercule-api-1234567890
```

## Step 5: Test the Deployment

```bash
# Get your function URL
FUNCTION_URL=$(az functionapp show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query defaultHostName \
  --output tsv)

# Test health endpoint
curl https://$FUNCTION_URL/health

# Test analyze endpoint
curl -X POST https://$FUNCTION_URL/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Step 6: Update Frontend

Update the frontend to use your Azure Function URL:

1. Create a production environment file:
```bash
# frontend/.env.production
VITE_API_URL=https://your-function-app.azurewebsites.net
```

2. Build the frontend:
```bash
cd frontend
npm run build
```

3. The built extension will be in `frontend/dist/`

## Troubleshooting

### "No module named 'azure.functions'"
Ensure requirements.txt includes `azure-functions>=1.17.0`

### CORS Errors
Add `ALLOWED_ORIGINS=*` to application settings or specify your extension ID:
```
ALLOWED_ORIGINS=chrome-extension://your-extension-id
```

### Cosmos DB Connection Failed
1. Verify connection string is correct
2. Check firewall settings in Cosmos DB → Networking
3. Enable "Allow access from Azure services"

### Cold Start Delays
First request may take 10-30 seconds due to cold start.
Consider using Premium plan for consistent performance.

## Estimated Costs

For typical usage (~100 requests/day):

| Service | Estimated Cost |
|---------|---------------|
| Azure Functions (Consumption) | Free tier: 1M requests/month |
| Cosmos DB (Serverless) | ~$0.25/million RUs |
| Storage Account | ~$0.02/GB/month |
| **Total** | **~$1-5/month** |

## Security Best Practices

1. **Restrict CORS** to your extension ID only
2. **Enable HTTPS only** in Function App settings
3. **Use Azure Key Vault** for production secrets
4. **Enable Application Insights** for monitoring
5. **Set up alerts** for errors and performance
