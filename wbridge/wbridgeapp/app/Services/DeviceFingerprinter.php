<?php

declare(strict_types=1);

namespace App\Services;

use Illuminate\Http\Request;

class DeviceFingerprinter
{
    public function __construct(
        private Request $request
    ) {}

    public function generateFingerprint(): string
    {
        $components = [
            'user_agent' => $this->getUserAgent(),
            'ip_network' => $this->getNetworkFingerprint(),
            'accept_language' => $this->getAcceptLanguage(),
            'accept_encoding' => $this->getAcceptEncoding(),
        ];

        $fingerprint = implode('|', array_values($components));

        return hash('sha256', $fingerprint);
    }

    public function generateDeviceName(): string
    {
        $userAgent = $this->getUserAgent();

        // Parse browser and OS from user agent
        $browser = $this->parseBrowser($userAgent);
        $os = $this->parseOperatingSystem($userAgent);

        return trim("{$browser} on {$os}");
    }

    private function getUserAgent(): string
    {
        return $this->request->userAgent() ?? 'Unknown';
    }

    private function getNetworkFingerprint(): string
    {
        $ip = $this->request->ip() ?? '0.0.0.0';

        // For IPv4, use first 3 octets for network fingerprint
        if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4)) {
            $parts = explode('.', $ip);

            return implode('.', array_slice($parts, 0, 3)).'.x';
        }

        // For IPv6, use first 64 bits
        if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
            $parts = explode(':', $ip);

            return implode(':', array_slice($parts, 0, 4)).'::x';
        }

        return 'unknown';
    }

    private function getAcceptLanguage(): string
    {
        return $this->request->header('Accept-Language', 'unknown');
    }

    private function getAcceptEncoding(): string
    {
        return $this->request->header('Accept-Encoding', 'unknown');
    }

    private function parseBrowser(string $userAgent): string
    {
        $browsers = [
            'Edge' => '/Edg\/([\d.]+)/',
            'Chrome' => '/Chrome\/([\d.]+)/',
            'Firefox' => '/Firefox\/([\d.]+)/',
            'Safari' => '/Version\/([\d.]+).*Safari/',
            'Opera' => '/OPR\/([\d.]+)/',
            'Internet Explorer' => '/MSIE ([\d.]+)/',
        ];

        foreach ($browsers as $browser => $pattern) {
            if (preg_match($pattern, $userAgent, $matches)) {
                return $browser;
            }
        }

        return 'Unknown Browser';
    }

    private function parseOperatingSystem(string $userAgent): string
    {
        $systems = [
            'Windows 11' => '/Windows NT 10\.0.*Windows NT 10\.0/',
            'Windows 10' => '/Windows NT 10\.0/',
            'Windows 8.1' => '/Windows NT 6\.3/',
            'Windows 8' => '/Windows NT 6\.2/',
            'Windows 7' => '/Windows NT 6\.1/',
            'Windows Vista' => '/Windows NT 6\.0/',
            'Windows XP' => '/Windows NT 5\.1/',
            'macOS' => '/Mac OS X ([\d_]+)/',
            'Linux' => '/Linux/',
            'Android' => '/Android ([\d.]+)/',
            'iOS' => '/OS ([\d_]+) like Mac OS X/',
            'Ubuntu' => '/Ubuntu/',
        ];

        foreach ($systems as $os => $pattern) {
            if (preg_match($pattern, $userAgent)) {
                return $os;
            }
        }

        return 'Unknown OS';
    }

    public function getCurrentIpAddress(): string
    {
        return $this->request->ip() ?? '0.0.0.0';
    }

    public function isSimilarFingerprint(string $storedFingerprint, string $currentFingerprint): bool
    {
        // For now, require exact match
        // In the future, we could implement fuzzy matching for minor user agent changes
        return $storedFingerprint === $currentFingerprint;
    }
}
