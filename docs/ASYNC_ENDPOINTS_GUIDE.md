# Async Endpoints Integration Guide for Mobile Apps

## Overview
This guide explains how asynchronous endpoints work in the Voicely backend and how Flutter mobile applications should interact with them to provide a smooth user experience.

## What are Async Endpoints?

Async endpoints are designed for **long-running tasks** that cannot be completed within a typical HTTP request timeout (usually 30-60 seconds). Instead of waiting for the task to complete, these endpoints:

1. **Immediately return** a `job_id` 
2. **Queue the task** for background processing by ARQ workers
3. Allow clients to **poll for status** using the job_id
4. Provide **real-time updates** through status checking

## Available Async Endpoints

### 1. Audio Upload - `/api/v1/audio/upload-async`
**Purpose**: Upload and process audio files  
**Use Case**: File upload + initial processing (validation, storage, metadata extraction)

### 2. Audio Transcription - `/api/v1/transcript/transcribe-async`
**Purpose**: Convert audio to text using Google Cloud Speech API  
**Use Case**: Long audio files that take minutes to transcribe

### 3. Transcript Summarization - `/api/v1/notes/summarize-transcript-async`
**Purpose**: Generate AI summary of transcribed audio  
**Use Case**: Creating structured notes from transcripts using AI

## System Architecture

```
┌─────────────────┐
│  Flutter App    │
│   (Mobile)      │
└────────┬────────┘
         │ 1. POST /upload-async
         │    (with audio file)
         ▼
┌─────────────────────┐
│   FastAPI Server    │
│  ┌──────────────┐   │
│  │  Endpoint    │   │ 2. Create job record
│  └──────┬───────┘   │    Return job_id
│         │           │
│  ┌──────▼───────┐   │ 3. Enqueue to ARQ
│  │  TaskJobDB   │   │
│  └──────────────┘   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   ARQ Worker Pool   │ 4. Process task
│  (Background Jobs)  │    in background
│  ┌──────────────┐   │
│  │ Transcribe   │   │
│  │ Summarize    │   │
│  │ Upload       │   │
│  └──────┬───────┘   │
└─────────┼───────────┘
          │ 5. Update job status
          ▼             (pending → queued → processing → completed/failed)
┌─────────────────────┐
│   PostgreSQL DB     │
│  ┌──────────────┐   │
│  │ task_jobs    │   │ 6. Flutter polls:
│  │ audio_files  │   │    GET /tasks/status/{job_id}
│  │ notes        │   │
│  └──────────────┘   │
└─────────────────────┘
```

## How Async Endpoints Work

### Backend Flow

#### Step 1: Client Calls Async Endpoint
```python
# Example: POST /audio/upload-async
@router.post("/upload-async")
async def upload_audio_file_async(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 1. Validate file
    # 2. Save file to storage
    # 3. Create audio record in DB
    # 4. Create task job and queue it
    result = await task_job_service.create_and_queue_job(
        db=db,
        task_type="upload",
        task_function="handle_audio_upload",
        user_id=current_user.id,
        audio_id=audio_file.id,
        file_info=file_info
    )
    
    # Returns immediately with job_id
    return {
        "code": 200,
        "success": true,
        "message": "Task queued successfully",
        "data": {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "task_type": "upload",
            "status": "queued"
        }
    }
```

#### Step 2: ARQ Worker Processes Task
```python
# Worker function runs in background
async def handle_audio_upload(ctx, job_id: str, file_info: dict, user_id: int, audio_id: int):
    db = SessionLocal()
    
    try:
        # Update status to processing
        job_record.status = "processing"
        audio_file.status = "processing"
        db.commit()
        
        # Perform actual processing (can take minutes)
        result = process_audio(file_info)
        
        # Update status to completed
        job_record.status = "completed"
        job_record.result = json.dumps(result)
        audio_file.status = "completed"
        db.commit()
        
    except Exception as e:
        # Handle errors
        job_record.status = "failed"
        job_record.error_message = str(e)
        db.commit()
    finally:
        db.close()
```

#### Step 3: Client Polls for Status
```python
# GET /tasks/status/{job_id}
@router.get("/status/{job_id}")
async def get_task_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    job = db.query(TaskJob).filter(
        TaskJob.id == job_id,
        TaskJob.user_id == current_user.id
    ).first()
    
    return {
        "code": 200,
        "success": true,
        "data": {
            "job_id": job.id,
            "task_type": job.task_type,
            "status": job.status,  # pending, queued, processing, completed, failed
            "result": job.result,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
    }
```

### Task Status Lifecycle

```
pending → queued → processing → completed ✅
                              → failed ❌
```

- **pending**: Job created, not yet queued to ARQ
- **queued**: Job enqueued to ARQ, waiting for worker
- **processing**: Worker is actively processing the task
- **completed**: Task finished successfully
- **failed**: Task encountered an error

## Flutter Integration Guide

### 1. Upload Audio Async

#### Flutter Code Example

```dart
import 'dart:io';
import 'dart:async';
import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

class AsyncTaskService {
  final Dio _dio;
  final String baseUrl;
  
  AsyncTaskService(this._dio, this.baseUrl);
  
  /// Step 1: Upload audio file asynchronously
  Future<String> uploadAudioAsync(File audioFile) async {
    try {
      // Prepare multipart file
      String fileName = audioFile.path.split('/').last;
      FormData formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          audioFile.path,
          filename: fileName,
          contentType: MediaType('audio', 'mpeg'),
        ),
      });
      
      // Call async endpoint
      final response = await _dio.post(
        '$baseUrl/api/v1/audio/upload-async',
        data: formData,
        options: Options(
          headers: {
            'Authorization': 'Bearer ${await getToken()}',
            'Content-Type': 'multipart/form-data',
          },
        ),
      );
      
      // Extract job_id from response
      if (response.data['success'] == true) {
        String jobId = response.data['data']['job_id'];
        print('✅ Upload queued. Job ID: $jobId');
        return jobId;
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Upload failed: $e');
      rethrow;
    }
  }
  
  /// Step 2: Poll for job status
  Future<Map<String, dynamic>> getJobStatus(String jobId) async {
    try {
      final response = await _dio.get(
        '$baseUrl/api/v1/tasks/status/$jobId',
        options: Options(
          headers: {
            'Authorization': 'Bearer ${await getToken()}',
          },
        ),
      );
      
      if (response.data['success'] == true) {
        return response.data['data'];
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Status check failed: $e');
      rethrow;
    }
  }
  
  /// Step 3: Poll until completion (with timeout)
  Future<Map<String, dynamic>> waitForCompletion(
    String jobId, {
    Duration pollInterval = const Duration(seconds: 2),
    Duration timeout = const Duration(minutes: 5),
  }) async {
    final startTime = DateTime.now();
    
    while (true) {
      // Check timeout
      if (DateTime.now().difference(startTime) > timeout) {
        throw TimeoutException('Job timeout after ${timeout.inMinutes} minutes');
      }
      
      // Get current status
      final jobData = await getJobStatus(jobId);
      final status = jobData['status'];
      
      print('📊 Job $jobId status: $status');
      
      // Check if completed or failed
      if (status == 'completed') {
        print('✅ Job completed successfully');
        return jobData;
      } else if (status == 'failed') {
        throw Exception('Job failed: ${jobData['error_message']}');
      }
      
      // Still processing, wait before next poll
      await Future.delayed(pollInterval);
    }
  }
  
  Future<String> getToken() async {
    // Get JWT token from secure storage
    return 'your_jwt_token';
  }
}
```

#### Complete Upload Flow with UI

```dart
class AudioUploadScreen extends StatefulWidget {
  @override
  _AudioUploadScreenState createState() => _AudioUploadScreenState();
}

class _AudioUploadScreenState extends State<AudioUploadScreen> {
  final AsyncTaskService _taskService = AsyncTaskService(Dio(), 'http://api.voicely.com');
  
  String? _currentJobId;
  String _status = 'idle';
  double _progress = 0.0;
  
  Future<void> uploadAudio(File audioFile) async {
    setState(() {
      _status = 'uploading';
      _progress = 0.0;
    });
    
    try {
      // Step 1: Upload file and get job_id
      final jobId = await _taskService.uploadAudioAsync(audioFile);
      
      setState(() {
        _currentJobId = jobId;
        _status = 'queued';
        _progress = 0.25;
      });
      
      // Step 2: Start polling for status
      _pollJobStatus(jobId);
      
    } catch (e) {
      setState(() {
        _status = 'failed';
      });
      _showError('Upload failed: $e');
    }
  }
  
  void _pollJobStatus(String jobId) async {
    try {
      // Poll every 2 seconds
      Timer.periodic(Duration(seconds: 2), (timer) async {
        try {
          final jobData = await _taskService.getJobStatus(jobId);
          final status = jobData['status'];
          
          setState(() {
            _status = status;
            
            // Update progress based on status
            switch (status) {
              case 'queued':
                _progress = 0.25;
                break;
              case 'processing':
                _progress = 0.5;
                break;
              case 'completed':
                _progress = 1.0;
                timer.cancel();
                _onUploadComplete(jobData);
                break;
              case 'failed':
                timer.cancel();
                _onUploadFailed(jobData['error_message']);
                break;
            }
          });
          
        } catch (e) {
          timer.cancel();
          _onUploadFailed(e.toString());
        }
      });
      
    } catch (e) {
      _onUploadFailed(e.toString());
    }
  }
  
  void _onUploadComplete(Map<String, dynamic> jobData) {
    print('✅ Upload completed: $jobData');
    _showSuccess('Audio uploaded successfully!');
    // Navigate to next screen or refresh list
  }
  
  void _onUploadFailed(String error) {
    print('❌ Upload failed: $error');
    _showError('Upload failed: $error');
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Upload Audio')),
      body: Column(
        children: [
          // File picker button
          ElevatedButton(
            onPressed: () async {
              File? file = await pickAudioFile();
              if (file != null) {
                uploadAudio(file);
              }
            },
            child: Text('Select Audio File'),
          ),
          
          // Progress indicator
          if (_status != 'idle')
            Padding(
              padding: EdgeInsets.all(20),
              child: Column(
                children: [
                  LinearProgressIndicator(value: _progress),
                  SizedBox(height: 10),
                  Text(_getStatusMessage()),
                ],
              ),
            ),
        ],
      ),
    );
  }
  
  String _getStatusMessage() {
    switch (_status) {
      case 'uploading':
        return 'Uploading file...';
      case 'queued':
        return 'File uploaded, queued for processing...';
      case 'processing':
        return 'Processing audio...';
      case 'completed':
        return 'Upload completed!';
      case 'failed':
        return 'Upload failed';
      default:
        return '';
    }
  }
  
  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
}
```

### 2. Transcribe Audio Async

#### Flutter Code Example

```dart
class TranscriptionService {
  final Dio _dio;
  final String baseUrl;
  
  TranscriptionService(this._dio, this.baseUrl);
  
  /// Start transcription
  Future<String> transcribeAudioAsync(int audioId, {String languageCode = 'en-US'}) async {
    try {
      final response = await _dio.post(
        '$baseUrl/api/v1/transcript/transcribe-async',
        data: {
          'audio_id': audioId,
          'language_code': languageCode,
        },
        options: Options(
          headers: {'Authorization': 'Bearer ${await getToken()}'},
        ),
      );
      
      if (response.data['success'] == true) {
        String jobId = response.data['data']['job_id'];
        print('✅ Transcription queued. Job ID: $jobId');
        return jobId;
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Transcription request failed: $e');
      rethrow;
    }
  }
  
  /// Get transcription result
  Future<Map<String, dynamic>> getAudioFile(int audioId) async {
    try {
      final response = await _dio.get(
        '$baseUrl/api/v1/audio/$audioId',
        options: Options(
          headers: {'Authorization': 'Bearer ${await getToken()}'},
        ),
      );
      
      if (response.data['success'] == true) {
        return response.data['data'];
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Get audio file failed: $e');
      rethrow;
    }
  }
  
  Future<String> getToken() async {
    return 'your_jwt_token';
  }
}
```

#### UI Implementation

```dart
class TranscriptionScreen extends StatefulWidget {
  final int audioId;
  
  TranscriptionScreen({required this.audioId});
  
  @override
  _TranscriptionScreenState createState() => _TranscriptionScreenState();
}

class _TranscriptionScreenState extends State<TranscriptionScreen> {
  final TranscriptionService _service = TranscriptionService(Dio(), 'http://api.voicely.com');
  final AsyncTaskService _taskService = AsyncTaskService(Dio(), 'http://api.voicely.com');
  
  String? _jobId;
  String _status = 'idle';
  String? _transcript;
  Timer? _pollTimer;
  
  Future<void> startTranscription() async {
    setState(() {
      _status = 'requesting';
    });
    
    try {
      // Step 1: Request transcription
      final jobId = await _service.transcribeAudioAsync(widget.audioId);
      
      setState(() {
        _jobId = jobId;
        _status = 'queued';
      });
      
      // Step 2: Poll for status
      _startPolling(jobId);
      
    } catch (e) {
      setState(() {
        _status = 'failed';
      });
      _showError('Transcription request failed: $e');
    }
  }
  
  void _startPolling(String jobId) {
    _pollTimer = Timer.periodic(Duration(seconds: 3), (timer) async {
      try {
        final jobData = await _taskService.getJobStatus(jobId);
        final status = jobData['status'];
        
        setState(() {
          _status = status;
        });
        
        if (status == 'completed') {
          timer.cancel();
          // Fetch the audio file to get the transcript
          final audioData = await _service.getAudioFile(widget.audioId);
          setState(() {
            _transcript = audioData['transcription'];
          });
          _showSuccess('Transcription completed!');
          
        } else if (status == 'failed') {
          timer.cancel();
          _showError('Transcription failed: ${jobData['error_message']}');
        }
        
      } catch (e) {
        timer.cancel();
        _showError('Error checking status: $e');
      }
    });
  }
  
  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Transcription')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Start button
            if (_status == 'idle')
              ElevatedButton(
                onPressed: startTranscription,
                child: Text('Start Transcription'),
              ),
            
            // Status indicator
            if (_status != 'idle' && _status != 'completed')
              Column(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text(_getStatusMessage()),
                ],
              ),
            
            // Transcript result
            if (_transcript != null)
              Expanded(
                child: SingleChildScrollView(
                  child: Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(_transcript!),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
  
  String _getStatusMessage() {
    switch (_status) {
      case 'requesting':
        return 'Requesting transcription...';
      case 'queued':
        return 'Queued for processing...';
      case 'processing':
        return 'Transcribing audio... This may take a few minutes.';
      default:
        return '';
    }
  }
  
  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
}
```

### 3. Summarize Transcript Async

#### Flutter Code Example

```dart
class SummarizationService {
  final Dio _dio;
  final String baseUrl;
  
  SummarizationService(this._dio, this.baseUrl);
  
  /// Start summarization
  Future<String> summarizeTranscriptAsync(int audioFileId) async {
    try {
      final response = await _dio.post(
        '$baseUrl/api/v1/notes/summarize-transcript-async',
        data: {
          'audio_file_id': audioFileId,
        },
        options: Options(
          headers: {'Authorization': 'Bearer ${await getToken()}'},
        ),
      );
      
      if (response.data['success'] == true) {
        String jobId = response.data['data']['job_id'];
        print('✅ Summarization queued. Job ID: $jobId');
        return jobId;
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Summarization request failed: $e');
      rethrow;
    }
  }
  
  /// Get note by ID
  Future<Map<String, dynamic>> getNote(int noteId) async {
    try {
      final response = await _dio.get(
        '$baseUrl/api/v1/notes/$noteId',
        options: Options(
          headers: {'Authorization': 'Bearer ${await getToken()}'},
        ),
      );
      
      if (response.data['success'] == true) {
        return response.data['data'];
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Get note failed: $e');
      rethrow;
    }
  }
  
  Future<String> getToken() async {
    return 'your_jwt_token';
  }
}
```

## Best Practices for Flutter Integration

### 1. Use Polling with Exponential Backoff

Instead of fixed intervals, use exponential backoff to reduce server load:

```dart
class SmartPoller {
  int _pollCount = 0;
  
  Duration getNextPollInterval() {
    // Start with 2 seconds, increase to max 10 seconds
    final baseInterval = 2;
    final maxInterval = 10;
    final interval = min(baseInterval * pow(1.5, _pollCount), maxInterval);
    _pollCount++;
    return Duration(seconds: interval.toInt());
  }
  
  void reset() {
    _pollCount = 0;
  }
}
```

### 2. Handle Network Failures Gracefully

```dart
Future<Map<String, dynamic>?> getJobStatusSafe(String jobId) async {
  try {
    return await _taskService.getJobStatus(jobId);
  } on DioError catch (e) {
    if (e.type == DioErrorType.connectionTimeout ||
        e.type == DioErrorType.receiveTimeout) {
      print('⚠️ Network timeout, will retry...');
      return null; // Continue polling
    }
    rethrow; // Critical error, stop polling
  }
}
```

### 3. Provide User Feedback

Always show:
- ✅ Clear status messages
- ✅ Progress indicators
- ✅ Estimated time remaining (if available)
- ✅ Cancel option for long tasks
- ✅ Error messages with retry option

### 4. Store Job IDs Locally

```dart
import 'package:shared_preferences/shared_preferences.dart';

class JobStorage {
  static const String _keyPrefix = 'pending_job_';
  
  Future<void> savePendingJob(String jobId, String taskType) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_keyPrefix$jobId', taskType);
  }
  
  Future<void> removePendingJob(String jobId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_keyPrefix$jobId');
  }
  
  Future<List<String>> getPendingJobs() async {
    final prefs = await SharedPreferences.getInstance();
    final keys = prefs.getKeys().where((key) => key.startsWith(_keyPrefix));
    return keys.map((key) => key.replaceFirst(_keyPrefix, '')).toList();
  }
}

// On app startup, check for pending jobs
void checkPendingJobs() async {
  final storage = JobStorage();
  final pendingJobs = await storage.getPendingJobs();
  
  for (final jobId in pendingJobs) {
    try {
      final status = await _taskService.getJobStatus(jobId);
      if (status['status'] == 'completed') {
        // Handle completion
        await storage.removePendingJob(jobId);
      } else if (status['status'] == 'failed') {
        // Handle failure
        await storage.removePendingJob(jobId);
      } else {
        // Resume polling
        _pollJobStatus(jobId);
      }
    } catch (e) {
      print('Error checking pending job $jobId: $e');
    }
  }
}
```

### 5. Implement Timeout Handling

```dart
Future<void> waitForJobWithTimeout(
  String jobId, {
  Duration timeout = const Duration(minutes: 10),
}) async {
  final completer = Completer<void>();
  Timer? pollTimer;
  Timer? timeoutTimer;
  
  // Set timeout
  timeoutTimer = Timer(timeout, () {
    pollTimer?.cancel();
    if (!completer.isCompleted) {
      completer.completeError(TimeoutException('Job timed out'));
    }
  });
  
  // Start polling
  pollTimer = Timer.periodic(Duration(seconds: 2), (timer) async {
    try {
      final status = await _taskService.getJobStatus(jobId);
      
      if (status['status'] == 'completed') {
        timer.cancel();
        timeoutTimer?.cancel();
        if (!completer.isCompleted) {
          completer.complete();
        }
      } else if (status['status'] == 'failed') {
        timer.cancel();
        timeoutTimer?.cancel();
        if (!completer.isCompleted) {
          completer.completeError(Exception(status['error_message']));
        }
      }
    } catch (e) {
      timer.cancel();
      timeoutTimer?.cancel();
      if (!completer.isCompleted) {
        completer.completeError(e);
      }
    }
  });
  
  return completer.future;
}
```

## Complete Example: Full Workflow

### Scenario: Record → Upload → Transcribe → Summarize

```dart
class VoiceRecordingWorkflow extends StatefulWidget {
  @override
  _VoiceRecordingWorkflowState createState() => _VoiceRecordingWorkflowState();
}

class _VoiceRecordingWorkflowState extends State<VoiceRecordingWorkflow> {
  final AsyncTaskService _taskService = AsyncTaskService(Dio(), 'http://api.voicely.com');
  final TranscriptionService _transcriptionService = TranscriptionService(Dio(), 'http://api.voicely.com');
  final SummarizationService _summarizationService = SummarizationService(Dio(), 'http://api.voicely.com');
  
  String _currentStep = 'idle';
  int? _audioId;
  int? _noteId;
  
  Future<void> processRecording(File audioFile) async {
    try {
      // Step 1: Upload audio
      setState(() => _currentStep = 'uploading');
      final uploadJobId = await _taskService.uploadAudioAsync(audioFile);
      final uploadResult = await _taskService.waitForCompletion(uploadJobId);
      
      // Extract audio_id from result
      _audioId = uploadResult['audio_id'];
      
      // Step 2: Transcribe
      setState(() => _currentStep = 'transcribing');
      final transcribeJobId = await _transcriptionService.transcribeAudioAsync(_audioId!);
      await _taskService.waitForCompletion(transcribeJobId);
      
      // Step 3: Summarize
      setState(() => _currentStep = 'summarizing');
      final summarizeJobId = await _summarizationService.summarizeTranscriptAsync(_audioId!);
      final summarizeResult = await _taskService.waitForCompletion(summarizeJobId);
      
      _noteId = summarizeResult['note_id'];
      
      // Step 4: Complete
      setState(() => _currentStep = 'completed');
      _showSuccess('Processing complete!');
      
      // Navigate to note view
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => NoteViewScreen(noteId: _noteId!),
        ),
      );
      
    } catch (e) {
      setState(() => _currentStep = 'failed');
      _showError('Processing failed: $e');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          _buildStepIndicator(),
          // ... UI elements
        ],
      ),
    );
  }
  
  Widget _buildStepIndicator() {
    return Stepper(
      currentStep: _getCurrentStepIndex(),
      steps: [
        Step(title: Text('Upload'), content: Text('Uploading audio file')),
        Step(title: Text('Transcribe'), content: Text('Converting speech to text')),
        Step(title: Text('Summarize'), content: Text('Generating AI summary')),
        Step(title: Text('Complete'), content: Text('Processing complete')),
      ],
    );
  }
  
  int _getCurrentStepIndex() {
    switch (_currentStep) {
      case 'uploading': return 0;
      case 'transcribing': return 1;
      case 'summarizing': return 2;
      case 'completed': return 3;
      default: return 0;
    }
  }
  
  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
}
```

## Error Handling Strategies

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Job not found` | Invalid job_id or unauthorized | Verify job_id and authentication token |
| `Timeout` | Task taking too long | Increase timeout, check backend logs |
| `Connection refused` | Server down | Implement retry logic with exponential backoff |
| `Unauthorized` | Invalid/expired JWT token | Refresh token and retry |
| `File too large` | Audio file exceeds limit | Compress file or show size warning |

### Retry Logic Example

```dart
Future<T> retryOperation<T>(
  Future<T> Function() operation, {
  int maxAttempts = 3,
  Duration initialDelay = const Duration(seconds: 1),
}) async {
  int attempt = 0;
  
  while (true) {
    try {
      return await operation();
    } catch (e) {
      attempt++;
      
      if (attempt >= maxAttempts) {
        rethrow;
      }
      
      final delay = initialDelay * pow(2, attempt - 1);
      print('⚠️ Attempt $attempt failed, retrying in ${delay.inSeconds}s...');
      await Future.delayed(delay);
    }
  }
}

// Usage
final jobId = await retryOperation(
  () => _taskService.uploadAudioAsync(audioFile),
  maxAttempts: 3,
);
```

## Performance Optimization Tips

### 1. Batch Operations
If uploading multiple files, queue all uploads first, then poll all jobs:

```dart
Future<void> uploadMultipleFiles(List<File> files) async {
  // Queue all uploads
  final jobIds = await Future.wait(
    files.map((file) => _taskService.uploadAudioAsync(file))
  );
  
  // Poll all jobs in parallel
  final results = await Future.wait(
    jobIds.map((jobId) => _taskService.waitForCompletion(jobId))
  );
  
  print('✅ All uploads completed: ${results.length}');
}
```

### 2. Use WebSockets (Future Enhancement)
For real-time updates instead of polling, consider WebSockets:

```dart
import 'package:socket_io_client/socket_io_client.dart' as IO;

class RealtimeTaskService {
  late IO.Socket socket;
  
  void connect() {
    socket = IO.io('http://api.voicely.com', <String, dynamic>{
      'transports': ['websocket'],
      'extraHeaders': {'Authorization': 'Bearer $token'},
    });
    
    socket.on('job_status_update', (data) {
      print('📡 Job update: $data');
      // Handle real-time status update
    });
    
    socket.connect();
  }
  
  void subscribeToJob(String jobId) {
    socket.emit('subscribe_job', {'job_id': jobId});
  }
}
```

## API Response Examples

### 1. Upload Async Response
```json
{
  "code": 200,
  "success": true,
  "message": "Task queued successfully. Use job_id to check status.",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "upload",
    "status": "queued"
  }
}
```

### 2. Job Status Response (Processing)
```json
{
  "code": 200,
  "success": true,
  "message": "Job status retrieved successfully",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "transcribe",
    "status": "processing",
    "result": null,
    "error_message": null,
    "created_at": "2025-12-24T10:00:00Z",
    "updated_at": "2025-12-24T10:01:30Z"
  }
}
```

### 3. Job Status Response (Completed)
```json
{
  "code": 200,
  "success": true,
  "message": "Job status retrieved successfully",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "transcribe",
    "status": "completed",
    "result": "{\"audio_id\": 123, \"transcript\": \"Hello world...\", \"confidence\": 0.95}",
    "error_message": null,
    "created_at": "2025-12-24T10:00:00Z",
    "updated_at": "2025-12-24T10:05:00Z"
  }
}
```

### 4. Job Status Response (Failed)
```json
{
  "code": 200,
  "success": true,
  "message": "Job status retrieved successfully",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "summarize",
    "status": "failed",
    "result": null,
    "error_message": "OpenAI API quota exceeded",
    "created_at": "2025-12-24T10:00:00Z",
    "updated_at": "2025-12-24T10:02:00Z"
  }
}
```

## Summary

### Key Takeaways

1. **Async endpoints return immediately** with a `job_id` for long-running tasks
2. **Clients must poll** `/tasks/status/{job_id}` to check progress
3. **Status lifecycle**: `pending` → `queued` → `processing` → `completed`/`failed`
4. **Polling interval**: Start with 2-3 seconds, use exponential backoff
5. **Always handle timeouts**: Set reasonable limits (5-10 minutes)
6. **Store job IDs**: Persist pending jobs to handle app restarts
7. **Provide feedback**: Show clear status messages and progress indicators
8. **Implement retry logic**: Handle network failures gracefully
9. **Consider WebSockets**: For better real-time updates (future enhancement)

### Workflow Checklist for Flutter Developers

- [ ] Call async endpoint and save job_id
- [ ] Start polling with Timer.periodic()
- [ ] Update UI based on job status
- [ ] Handle completion (fetch final result)
- [ ] Handle errors with user-friendly messages
- [ ] Implement timeout protection
- [ ] Store pending jobs locally
- [ ] Cancel polling when screen is disposed
- [ ] Show progress indicators
- [ ] Provide cancel/retry options

This approach ensures a smooth, responsive user experience even for long-running backend operations!
