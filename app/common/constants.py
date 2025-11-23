
class AIPrompts:
    """AI-related prompts for various operations."""
    
    SUMMARY_SYSTEM_PROMPT = """Bạn là Trợ lý Tóm tắt Chuyên nghiệp. Tạo bản tóm tắt HTML ngắn gọn, chính xác, trung lập, đọc hiểu độc lập.

        ## NGUYÊN TẮC CỐT LÕI

        1. **Hiểu sâu nội dung**
        - Xác định mục đích chính & thông điệp của tác giả
        - Nắm cấu trúc lập luận (vấn đề→giải pháp, nguyên nhân→kết quả, v.v.)

        2. **Lọc thông tin**
        - Phân biệt ý chính vs chi tiết phụ trợ
        - Chỉ giữ số liệu/ví dụ nếu thiết yếu cho hiểu biết
        - Loại bỏ thông tin lặp lại hoặc tiếp tuyến

        3. **Viết súc tích**
        - Đạt độ dài mục tiêu (sẽ được chỉ định)
        - Mỗi câu phải mang thông tin, tránh từ thừa
        - Dùng ngôn ngữ rõ ràng, cụ thể

        4. **Giữ khách quan**
        - Không thêm ý kiến cá nhân hoặc diễn giải chủ quan
        - Trung thành với giọng điệu & mức độ nhấn mạnh của tác giả
        - Không phóng đại hoặc hạ thấp bất kỳ luận điểm nào

        5. **Đảm bảo chính xác**
        - Không xuyên tạc ý nghĩa gốc
        - Không thêm thông tin ngoài văn bản nguồn
        - Tự kiểm tra sau khi viết xem có mâu thuẫn với bản gốc

        6. **Tạo tính mạch lạc**
        - Người đọc hiểu được mà không cần văn bản gốc
        - Sắp xếp ý logic, dùng từ nối phù hợp
        - Giữ nguyên trình tự ý chính của tác giả trừ khi cần tái cấu trúc để rõ hơn

        ## QUY TRÌNH 5 BƯỚC

        **A. Đọc khảo sát**: Nắm ý tổng thể, mục đích, cấu trúc
        **B. Đánh dấu ý chính**: Rút câu chủ đề mỗi đoạn, gạch chi tiết có thể bỏ
        **C. Sắp xếp & gom nhóm**: Tổ chức ý theo logic, giữ mức độ nhấn mạnh
        **D. Viết nháp**: Tuân thủ định dạng & độ dài được chỉ định
        **E. Tự kiểm tra 5 câu hỏi**:
        - Có phản ánh đúng mục đích tác giả?
        - Các ý chính được giữ nguyên?
        - Đạt độ dài yêu cầu?
        - Khách quan & trung lập?
        - Mạch lạc & đọc hiểu độc lập?

        ## ĐỊNH DẠNG HTML

        **Cấu trúc gốc**: `<article lang="{language}">...</article>`

        **Thẻ được phép**: 
        - Cấu trúc: `<section>`, `<h2>`, `<h3>`, `<p>`, `<hr>`
        - Danh sách: `<ul>`, `<ol>`, `<li>`
        - Định nghĩa: `<dl>`, `<dt>`, `<dd>` (cho thuật ngữ/khái niệm)
        - Định dạng: `<strong>`, `<em>`, `<small>`, `<blockquote>` (trích dẫn quan trọng)

        **Không được dùng**: CSS, JavaScript, `<img>`, `<iframe>`, `<style>`, `<script>`

        **Hai dạng đầu ra**:
        1. **Paragraph**: 1-3 đoạn văn trong `<section><p>...</p></section>`
        2. **Bullet**: Danh sách `<ul><li>...</li></ul>`, mỗi bullet là 1 ý chính hoàn chỉnh

        **Phần tùy chọn** (nếu được yêu cầu):
        - Từ khóa: `<hr><section><h2>Từ khóa</h2><p><small>tối đa 5 cụm</small></p></section>`
        - Trích dẫn nổi bật: `<blockquote>Câu quan trọng từ văn bản gốc</blockquote>`

        ## XỬ LÝ TRƯỜNG HỢP ĐẶC BIỆT

        - **Văn bản quá ngắn** (<200 từ): Tóm tắt chỉ nên ngắn hơn 20-30%, có thể chỉ tái cấu trúc
        - **Văn bản rất dài** (>5000 từ): Ưu tiên ý chính ở mở bài & kết bài, tóm gọn phần thân
        - **Đa chủ đề**: Tạo các `<section>` riêng với `<h2>` cho từng chủ đề lớn
        - **Có bảng/số liệu**: Chuyển sang danh sách (`<ul>`) hoặc mô tả bằng văn xuôi
        - **Văn bản mơ hồ**: Tóm tắt theo cách hiểu hợp lý nhất, không bịa thêm

        ## RÀNG BUỘC TUYỆT ĐỐI

        ✗ Không thêm thông tin ngoài văn bản gốc
        ✗ Không copy-paste nguyên văn dài (trừ trích dẫn ngắn trong `<blockquote>`)
        ✗ Không đưa ra đánh giá chất lượng văn bản gốc
        ✗ Không giải thích quy trình tóm tắt trong output
        ✗ Không xuất markdown hay code block - chỉ HTML thuần
    """

    SUMMARY_USER_PROMPT = """Tóm tắt văn bản sau thành HTML theo đúng hướng dẫn trong System Prompt.

        ## CẤU HÌNH

        **Độc giả mục tiêu**: [mặc định: đại chúng có hiểu biết cơ bản]
        **Dạng đầu ra**: [paragraph / bullet]
        **Độ dài mục tiêu**: [~50{{%}} bản gốc]
        **Ngôn ngữ**: [vi / en / ...]
        **Số bullet tối đa**: [mặc định: 5] _(chỉ áp dụng nếu chọn bullet)_
        **Giữ số liệu cụ thể**: [có / không - mặc định: có]
        **Thêm từ khóa**: [có / không - mặc định: không]
        **Thêm trích dẫn nổi bật**: [có / không - mặc định: không]

        ---

        ## VĂN BẢN GỐC

        {content}

        ---

        ## YÊU CẦU ĐẦU RA

        Trả về **duy nhất** đoạn HTML từ `<article lang="...">` đến `</article>`.
        Không kèm giải thích, không bọc trong markdown/code block.
    """


class TranscriptionConfig:
    """Transcription service configuration constants."""
    
    # File size limits
    MAX_SYNC_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_ASYNC_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    MAX_GCS_FALLBACK_SIZE = 2 * 1024 * 1024  # 2MB
    
    # Duration limits
    MAX_SYNC_DURATION = 60  # 60 seconds
    MAX_ASYNC_DURATION = 300  # 5 minutes
    MAX_GCS_DURATION = 480 * 60  # 480 minutes (8 hours)
    
    # Audio settings
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_ENCODING = "LINEAR16"
    
    # Timeout settings
    LONG_RUNNING_TIMEOUT = 900  # 15 minutes
    GCS_TRANSCRIPTION_TIMEOUT = 900  # 15 minutes


class AudioConfig:
    """Audio file configuration constants."""
    
    # Supported formats
    SUPPORTED_FORMATS = [
        'wav', 'mp3', 'flac', 'ogg', 'opus', 
        'm4a', 'aac', 'wma', 'webm'
    ]
    
    # Format categories
    LOSSLESS_FORMATS = ['wav', 'flac']
    COMPRESSED_FORMATS = ['mp3', 'aac', 'm4a', 'ogg', 'opus']
    
    # Conversion settings
    CONVERT_FORMATS = ['mp3', 'm4a', 'aac']  # Formats to convert for better recognition
    CONVERTED_SAMPLE_RATE = 16000
    CONVERTED_CHANNELS = 1  # Mono


class FileUploadConfig:
    """File upload configuration constants."""
    
    # Upload limits
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_FILE_NAME_LENGTH = 255
    
    # Allowed MIME types
    ALLOWED_AUDIO_MIME_TYPES = [
        'audio/wav',
        'audio/mpeg',
        'audio/mp3',
        'audio/flac',
        'audio/ogg',
        'audio/opus',
        'audio/m4a',
        'audio/aac',
        'audio/x-wav',
        'audio/x-m4a',
    ]
    
    # Upload paths
    UPLOAD_BASE_DIR = "uploads"
    AUDIO_UPLOAD_DIR = "uploads/audio"
    TEMP_UPLOAD_DIR = "uploads/temp"


class LanguageCodes:
    """Supported language codes for transcription."""
    
    SUPPORTED_LANGUAGES = [
        {"code": "en-US", "name": "English (US)"},
        {"code": "en-GB", "name": "English (UK)"},
        {"code": "vi-VN", "name": "Vietnamese"},
        {"code": "es-ES", "name": "Spanish (Spain)"},
        {"code": "es-MX", "name": "Spanish (Mexico)"},
        {"code": "fr-FR", "name": "French"},
        {"code": "de-DE", "name": "German"},
        {"code": "ja-JP", "name": "Japanese"},
        {"code": "ko-KR", "name": "Korean"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "zh-TW", "name": "Chinese (Traditional)"},
        {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        {"code": "pt-PT", "name": "Portuguese (Portugal)"},
        {"code": "it-IT", "name": "Italian"},
        {"code": "ru-RU", "name": "Russian"},
        {"code": "ar-SA", "name": "Arabic"},
        {"code": "hi-IN", "name": "Hindi"},
        {"code": "th-TH", "name": "Thai"},
        {"code": "id-ID", "name": "Indonesian"},
    ]
    
    DEFAULT_LANGUAGE = "en-US"


class StatusCodes:
    """Status codes for various operations."""
    
    # Audio processing status
    AUDIO_PENDING = "pending"
    AUDIO_PROCESSING = "processing"
    AUDIO_COMPLETED = "completed"
    AUDIO_FAILED = "failed"
    
    # Transcription status
    TRANSCRIPTION_PENDING = "pending"
    TRANSCRIPTION_IN_PROGRESS = "in_progress"
    TRANSCRIPTION_COMPLETED = "completed"
    TRANSCRIPTION_FAILED = "failed"
    
    # Note status
    NOTE_ACTIVE = "active"
    NOTE_ARCHIVED = "archived"
    NOTE_DELETED = "deleted"


class ErrorMessages:
    """Common error messages."""
    
    # Authentication errors
    INVALID_CREDENTIALS = "Invalid email or password"
    UNAUTHORIZED = "Not authenticated"
    FORBIDDEN = "Permission denied"
    TOKEN_EXPIRED = "Token has expired"
    INVALID_TOKEN = "Invalid token"
    
    # File errors
    FILE_NOT_FOUND = "File not found"
    FILE_TOO_LARGE = "File size exceeds maximum allowed size"
    INVALID_FILE_FORMAT = "Invalid file format"
    UPLOAD_FAILED = "File upload failed"
    
    # Transcription errors
    TRANSCRIPTION_UNAVAILABLE = "Transcription service is not available"
    TRANSCRIPTION_FAILED = "Transcription failed"
    GCS_NOT_CONFIGURED = "Google Cloud Storage not configured"
    GCS_UPLOAD_FAILED = "Failed to upload file to Google Cloud Storage"
    
    # Database errors
    DATABASE_ERROR = "Database operation failed"
    RECORD_NOT_FOUND = "Record not found"
    DUPLICATE_ENTRY = "Record already exists"
    
    # General errors
    INTERNAL_ERROR = "Internal server error"
    VALIDATION_ERROR = "Validation error"
    BAD_REQUEST = "Bad request"


class SuccessMessages:
    """Common success messages."""
    
    # Authentication
    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logout successful"
    SIGNUP_SUCCESS = "Account created successfully"
    
    # File operations
    UPLOAD_SUCCESS = "File uploaded successfully"
    DELETE_SUCCESS = "File deleted successfully"
    
    # Transcription
    TRANSCRIPTION_SUCCESS = "Transcription completed successfully"
    TRANSCRIPTION_STARTED = "Transcription started"
    
    # Note operations
    NOTE_CREATED = "Note created successfully"
    NOTE_UPDATED = "Note updated successfully"
    NOTE_DELETED = "Note deleted successfully"


class RegexPatterns:
    """Common regex patterns for validation."""
    
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PASSWORD = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$'  # Min 8 chars, 1 letter, 1 number
    PHONE = r'^\+?1?\d{9,15}$'
    URL = r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'


class CacheKeys:
    """Cache key templates."""
    
    USER_PROFILE = "user:profile:{user_id}"
    AUDIO_FILE = "audio:file:{audio_id}"
    TRANSCRIPTION = "transcription:{audio_id}"
    NOTE = "note:{note_id}"
    USER_NOTES = "user:notes:{user_id}"
    
    # Cache TTL (in seconds)
    DEFAULT_TTL = 3600  # 1 hour
    SHORT_TTL = 300  # 5 minutes
    LONG_TTL = 86400  # 24 hours


class PaginationDefaults:
    """Default pagination settings."""
    
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1
