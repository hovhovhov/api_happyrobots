# Carrier Sales API - HappyRobot Integration

Backend API to automate carrier load sales via HappyRobot platform.

## 🚀 Architecture

```
HappyRobot Workflow → Flask API → Loads Database
                    ↓
              Analytics Dashboard
```

## 📋 API Endpoints

### 1. Health Check
```
GET /health
```
Verifies that the API is online.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T10:00:00",
  "service": "Carrier Sales API"
}
```

---

### 2. Verify Carrier
```
GET /api/verify-carrier?mc_number=123456&dot_number=789012
Headers: X-API-Key: your-api-key
```

Verifies a carrier using the FMCSA API.

**Query Parameters:**
- `mc_number` (optional): Carrier's MC number
- `dot_number` (optional): Carrier's DOT number

**Response:**
```json
{
  "success": true,
  "verified": true,
  "carrier_data": {
    "mc_number": "123456",
    "dot_number": "789012",
    "legal_name": "ABC Trucking LLC",
    "operating_status": "ACTIVE",
    "out_of_service": false
  },
  "timestamp": "2025-11-07T10:00:00"
}
```

---

### 3. Search Loads
```
GET /api/loads?origin_city=Chicago&destination_city=Dallas&equipment_type=Dry%20Van
Headers: X-API-Key: your-api-key
```

Searches for available loads based on criteria.

**Query Parameters:**
- `origin_city`: Origin city
- `origin_state`: Origin state
- `destination_city`: Destination city
- `destination_state`: Destination state
- `equipment_type`: Equipment type (Dry Van, Reefer, Flatbed)
- `commodity`: Commodity type
- `pickup_date`: Pickup date (ISO 8601 format)

**Response:**
```json
{
  "success": true,
  "count": 2,
  "loads": [
    {
      "load_id": "LOAD-001",
      "origin": "Chicago, IL",
      "destination": "Dallas, TX",
      "equipment_type": "Dry Van",
      "loadboard_rate": 2500,
      "pickup_datetime": "2025-11-10T08:00:00",
      "delivery_datetime": "2025-11-12T17:00:00",
      ...
    }
  ],
  "timestamp": "2025-11-07T10:00:00"
}
```

---

### 4. Get Load by ID
```
GET /api/loads/LOAD-001
Headers: X-API-Key: your-api-key
```

Retrieves a specific load by its ID.

---

### 5. Save Call Results
```
POST /api/call-results
Headers: X-API-Key: your-api-key
Content-Type: application/json
```

Saves call results from HappyRobot workflow.

**Body:**
```json
{
  "call_id": "call_123",
  "mc_number": "123456",
  "load_id": "LOAD-001",
  "outcome": "agreed",
  "sentiment": "positive",
  "agreed_rate": 2400,
  "negotiation_rounds": 2,
  "extracted_data": {
    "carrier_name": "ABC Trucking",
    "contact_person": "John Doe"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Call results saved successfully",
  "call_id": "call_20251107_100000",
  "timestamp": "2025-11-07T10:00:00"
}
```

---

### 6. Get Analytics
```
GET /api/analytics
Headers: X-API-Key: your-api-key
```

Retrieves analytics data for the dashboard.

**Response:**
```json
{
  "success": true,
  "analytics": {
    "total_calls": 50,
    "successful_calls": 35,
    "transferred_calls": 30,
    "conversion_rate": 70.0,
    "sentiment": {
      "positive": 30,
      "neutral": 15,
      "negative": 5,
      "positive_rate": 60.0
    },
    "negotiation": {
      "avg_rounds": 1.8,
      "avg_agreed_rate": 2350.50
    }
  },
  "timestamp": "2025-11-07T10:00:00"
}
```

---

### 7. Get All Calls
```
GET /api/calls?limit=10
Headers: X-API-Key: your-api-key
```

Retrieves the history of all calls.

---

## 🔧 Local Installation

### Prerequisites
- Python 3.11+
- pip

### Steps

1. **Clone/Create the project**
```bash
mkdir carrier-sales-api
cd carrier-sales-api
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Edit `.env` and change the API key:
```
API_KEY=your-secret-key-here
```

5. **Run the application**
```bash
python app.py
```

The API will be accessible at: `http://localhost:5000`

---

## 🐳 Docker

### Build the image
```bash
docker build -t carrier-sales-api .
```

### Run the container
```bash
docker run -p 5000:5000 -e API_KEY=your-secret-key carrier-sales-api
```

---

## ☁️ Deployment on Render.com

### Option 1: Deploy from GitHub

1. **Push code to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/carrier-sales-api.git
git push -u origin main
```

2. **Create a Render.com account**
   - Go to https://render.com
   - Sign up for free

3. **Create a new Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configuration:
     - **Name**: carrier-sales-api
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
     - **Plan**: Free

4. **Add environment variables**
   In the service settings:
   - `API_KEY`: your-secret-key
   - `FMCSA_API_KEY`: (optional)

5. **Deploy**
   Render will automatically deploy your app.
   You'll get a URL like: `https://carrier-sales-api.onrender.com`

### Option 2: Deploy via Docker on Render

1. In Render, select "Docker" as the environment
2. Render will automatically use your Dockerfile

---

## 🔐 Security

### API Key Authentication

All endpoints (except `/health`) require an API key in the header:
```
X-API-Key: your-secret-api-key
```

### Production recommendations:
1. ✅ Use HTTPS (automatic with Render)
2. ✅ Change the default API key
3. ✅ Obtain a real FMCSA API key
4. ✅ Add rate limiting
5. ✅ Implement more robust logging

---

## 📊 HappyRobot Integration

### Node Configuration:

#### 1. Node "Verify carrier and search loads"
- **Method**: GET
- **URL**: `https://your-api.onrender.com/api/verify-carrier`
- **Headers**: 
  - `X-API-Key`: your-secret-key
- **Query Parameters**: 
  - `mc_number`: `{{mc_number}}`
  - `dot_number`: `{{dot_number}}`

#### 2. Node "Find loads"
- **Method**: GET
- **URL**: `https://your-api.onrender.com/api/loads`
- **Headers**: 
  - `X-API-Key`: your-secret-key
- **Query Parameters**: 
  - `origin_city`: `{{origin_city}}`
  - `destination_city`: `{{destination_city}}`
  - `equipment_type`: `{{equipment_type}}`

#### 3. Node POST (Webhook) - Save Results
- **Method**: POST
- **URL**: `https://your-api.onrender.com/api/call-results`
- **Headers**: 
  - `X-API-Key`: your-secret-key
  - `Content-Type`: application/json
- **Body**: 
```json
{
  "mc_number": "{{mc_number}}",
  "load_id": "{{load_id}}",
  "outcome": "{{outcome}}",
  "sentiment": "{{sentiment}}",
  "agreed_rate": {{agreed_rate}},
  "negotiation_rounds": {{negotiation_rounds}}
}
```

---

## 🧪 Testing the API

### Using curl:
```bash
# Health check
curl http://localhost:5000/health

# Verify carrier
curl -H "X-API-Key: your-secret-api-key-change-this-in-production" \
  "http://localhost:5000/api/verify-carrier?mc_number=123456"

# Search loads
curl -H "X-API-Key: your-secret-api-key-change-this-in-production" \
  "http://localhost:5000/api/loads?origin_city=Chicago&equipment_type=Dry%20Van"

# Get analytics
curl -H "X-API-Key: your-secret-api-key-change-this-in-production" \
  "http://localhost:5000/api/analytics"
```

### Using Postman:
1. Import the API endpoints
2. Add header: `X-API-Key: your-secret-api-key-change-this-in-production`
3. Test each endpoint

---

## 📈 Dashboard (To be created - Objective 2)

The dashboard will be created separately and will use the endpoints:
- `GET /api/analytics` - For global metrics
- `GET /api/calls` - For call history

Suggested technologies for the dashboard:
- **React** + Chart.js
- **Streamlit** (Python)
- **Flask** + Plotly

---

## 🔄 Complete Workflow Flow

1. **Carrier calls** → HappyRobot receives inbound call
2. **Verification** → HappyRobot calls `GET /api/verify-carrier`
3. **API validates** → Returns carrier status (active/inactive)
4. **Load search** → HappyRobot calls `GET /api/loads` with criteria
5. **API searches** → Returns matching loads from database
6. **AI negotiates** → HappyRobot handles negotiation (up to 3 rounds)
7. **Agreement reached** → Transfer to sales rep
8. **Save results** → HappyRobot calls `POST /api/call-results`
9. **Dashboard updates** → Analytics available via `GET /api/analytics`

---

## 📝 TODO

- [x] Basic API endpoints
- [x] FMCSA verification
- [x] Load search
- [x] Save call results
- [x] Analytics
- [ ] Frontend dashboard
- [ ] Unit tests
- [ ] Rate limiting
- [ ] Advanced logging
- [ ] Swagger/OpenAPI documentation

---

## 🐛 Troubleshooting

### Common Issues:

**Issue:** API won't start
- **Solution:** Check if port 5000 is already in use. Kill the process or use a different port.

**Issue:** "Unauthorized" error
- **Solution:** Verify you're sending the correct API key in the `X-API-Key` header.

**Issue:** No loads returned
- **Solution:** Check that `loads.json` exists and contains data. Verify your search parameters.

**Issue:** FMCSA verification not working
- **Solution:** The API runs in demo mode without a real FMCSA API key. Get one from https://mobile.fmcsa.dot.gov/developer/

---

## 🤝 Support

For any questions about this project, contact: [your email]

---

## 📄 License

MIT License - Demo project for HappyRobot Technical Challenge