# AI Workflow Engine - AG-UI Integration

## 🚀 Quick Start

This project has been enhanced with **AG-UI protocol** for real-time, streaming AI agent interactions. You now have two interfaces:

### Legacy Interface (Still Available)
- **Streamlit UI**: `streamlit run legacy/ui.py`
- **CLI Submission**: `python legacy/submit.py --sample`

### New AG-UI Interface (Recommended)
- **Modern React Frontend**: Real-time streaming, interactive components
- **AG-UI Backend**: Event-driven agent protocol

## 🎯 AG-UI Setup & Usage

### 1. Install Dependencies

```bash
# Python dependencies (already installed if you used pip install -r requirements.txt)
pip install ag-ui-protocol fastapi uvicorn

# Frontend dependencies
cd frontend && npm install
```

### 2. Configure Environment

Make sure your `.env` file contains:
```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=deepseek/deepseek-chat-v3.1:free
```

### 3. Start the System

**Option A: Manual Start (Recommended for Development)**

Terminal 1 - Backend:
```bash
python start_backend.py
```

Terminal 2 - Frontend:
```bash
python start_frontend.py
```

**Option B: Direct Commands**

Backend:
```bash
cd backend && python ag_ui_server.py
```

Frontend:
```bash
cd frontend && npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🌟 New Features with AG-UI

### Real-time Document Processing
- **Streaming Responses**: Watch documents being processed in real-time
- **Live Progress Updates**: See each step of the workflow as it happens
- **Interactive Components**: Dynamic UI elements that adapt to workflow needs

### Enhanced Human-in-the-Loop
- **Real-time Review Queue**: New documents appear instantly
- **Inline Editing**: Edit extracted data directly in the UI
- **Live Notifications**: Get notified when documents need review
- **Collaborative Review**: Multiple users can work simultaneously

### Modern User Experience
- **Responsive Design**: Works on desktop and mobile
- **Dark/Light Theme**: Automatic theme adaptation
- **Sample Documents**: One-click sample invoice and support ticket loading
- **Real-time Status**: Live connection status and processing indicators

## 📋 How to Use

### Processing Documents

1. **Open Frontend**: Navigate to http://localhost:3000
2. **Select Document Processor Tab**
3. **Load Sample or Paste Content**:
   - Click "Load Sample Invoice" for a $4,068.75 invoice (will require review)
   - Click "Load Sample Support Ticket" for an irate customer (will require review)
   - Or paste your own document content
4. **Click "Process Document"**
5. **Watch Real-time Processing**: 
   - See AI extraction in progress
   - View extracted data as it's processed
   - Get validation results instantly

### Reviewing Documents

1. **Switch to Review Queue Tab**
2. **See Pending Reviews**: Documents requiring human attention appear automatically
3. **Review and Edit**: 
   - Click on a document card
   - Edit any incorrect extracted data
   - See validation reasons
4. **Approve or Reject**:
   - Click "Approve & Continue" to finalize
   - Click "Reject" to stop processing

## 🔧 Architecture Overview

### Backend Components
- **ag_ui_server.py**: Main AG-UI compatible server
- **DocumentWorkflowAgent**: Streams workflow execution as AG-UI events
- **Shared Database**: SQLite with AG-UI state management
- **Legacy Integration**: Wraps existing LangGraph workflow

### Frontend Components
- **DocumentProcessor**: Real-time document submission and processing
- **ReviewQueue**: Live human review interface
- **DocumentReviewCard**: Interactive document editing
- **AG-UI Client**: Handles streaming and state management

### Event Flow
1. **RUN_STARTED**: Workflow begins
2. **TEXT_MESSAGE_CHUNK**: Progress updates stream
3. **TOOL_CALL_CHUNK**: Structured data extraction
4. **GENERATIVE_UI**: Interactive review components
5. **HUMAN_INPUT_REQUIRED**: Pause for human review
6. **RUN_FINISHED**: Workflow completion

## 🧪 Testing

Run integration tests:
```bash
python test_integration.py
```

Test individual components:
```bash
# Test shared types
python -c "from shared.types import DocumentExtractedData; print('OK')"

# Test database
python -c "from shared.database import WorkflowDatabase; print('OK')"

# Test AG-UI server (requires backend running)
curl http://localhost:8000/api/workflows/pending
```

## 🚦 Troubleshooting

### Backend Issues
- **Import Errors**: Make sure you're running from project root
- **Database Errors**: Check `./checkpoints/` directory permissions
- **API Key Errors**: Verify `.env` file has `OPENROUTER_API_KEY`

### Frontend Issues
- **npm install fails**: Make sure Node.js 18+ is installed
- **Connection errors**: Ensure backend is running on port 8000
- **Build errors**: Check TypeScript and React versions

### Common Solutions
```bash
# Reset frontend dependencies
cd frontend && rm -rf node_modules package-lock.json && npm install

# Reset database
rm -rf checkpoints/ && mkdir checkpoints

# Check backend health
curl http://localhost:8000/api/workflows/pending
```

## 📊 Comparison: Legacy vs AG-UI

| Feature | Legacy (Streamlit) | AG-UI (React) |
|---------|-------------------|---------------|
| Processing | Batch/Refresh | Real-time Streaming |
| UI Updates | Manual Refresh | Live Updates |
| Human Review | Form-based | Interactive Components |
| Collaboration | Single User | Multi-user |
| Mobile Support | Limited | Responsive |
| Developer Experience | Simple | Modern TypeScript |
| Performance | Page Reloads | Event-driven |
| Extensibility | Limited | Highly Extensible |

## 🔄 Migration Notes

- **Database Compatibility**: Both interfaces share the same SQLite database
- **Workflow State**: Existing workflows continue to work
- **API Compatibility**: All existing CLI tools still function
- **Gradual Migration**: You can use both interfaces simultaneously

## 🎯 Next Steps

The AG-UI integration is now complete and provides a solid foundation for building modern AI agent interfaces. Key capabilities achieved:

1. ✅ **Real-time Streaming**: Documents process with live updates
2. ✅ **Interactive Reviews**: Human-in-the-loop with rich UI components  
3. ✅ **Event-driven Architecture**: Scalable, production-ready design
4. ✅ **Modern Frontend**: React with TypeScript and responsive design
5. ✅ **Backward Compatibility**: Legacy tools and database remain functional

The system is ready for production use and can be extended with additional features like multi-agent coordination, collaborative editing, and advanced analytics.

---

**Built with ❤️ using AG-UI Protocol - Bridging AI agents and human interfaces**