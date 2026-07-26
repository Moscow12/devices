<?php
// Minimal API receiver

// Allow JSON and form requests
use function PHPSTORM_META\type;

header("Content-Type: application/json");

// Optional: Allow from any origin (useful for Postman/browser tests)
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

// Handle OPTIONS request (CORS preflight)
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Read incoming data
$data = [];

// If JSON input
$raw = file_get_contents("php://input");
if (!empty($raw) && ($json = json_decode($raw, true)) !== null) {
    $data = $json;
} else {
    // If form or query params
    $data = array_merge($_GET, $_POST);
}


// Decode JSON into PHP array
$data = json_decode($raw, true);

// Database credentials
$host = 'localhost'; // or your host
$username = 'root';
$password = 'ehms2gpitg2020';
$dbname = 'tshrp';
$conn = mysqli_connect($host, $username, $password, $dbname);
if (!$conn) {
    http_response_code(500);
    echo json_encode([
        "status" => "error",
        "message" => "Database connection failed: " . mysqli_connect_error()
    ]);
    exit;
}
$countErrors = 0;
foreach ($data as $value) {
    // Prevent SQL injection
    $user_id  = mysqli_real_escape_string($conn, $value['user_id']);
    $datetime = mysqli_real_escape_string($conn, $value['timestamp']);

    list($date, $time) = explode(' ', $datetime);

   $valuedate= $date; // Output: 2025-08-11
    $valuetime= $time; // Output: 06:58:00

    $datarecorded = mysqli_query($conn, "INSERT INTO attendances (user_id, clocktimestamp, clockdate, clocktime) VALUES ('$user_id', '$datetime', '$valuedate', '$valuetime')") or die(mysqli_error($conn));
    if ($datarecorded) {
        $countErrors++;
    }
}

if ($countErrors != 0) {
    echo json_encode([
        "status" => "Success",
        "message" => "All records inserted successfully",
        "total" => count($data),        
    ]);
} else {
    echo json_encode([
        "status" => "Failled",
        "message" => "Data insertion failed",
        "failed" => $countErrors. "==". $valuetime
    ]);
}

mysqli_close($conn);
?>