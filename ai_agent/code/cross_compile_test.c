/* cross_compile_test.c - A simple cross-platform C program */
#include <stdio.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
    #include <windows.h>
    #define OS_NAME "Windows"
#elif defined(__linux__)
    #include <sys/utsname.h>
    #define OS_NAME "Linux"
#elif defined(__ANDROID__)
    #define OS_NAME "Android"
#else
    #define OS_NAME "Unknown"
#endif

#define VERSION "1.0.0"
#define BUILD_TIMESTAMP __DATE__ " " __TIME__

int main(int argc, char *argv[]) {
    printf("========================================\n");
    printf("  ComputeHub Cross-Compile Test v%s\n", VERSION);
    printf("========================================\n");
    printf("  OS:       %s\n", OS_NAME);
    printf("  Build:    %s\n", BUILD_TIMESTAMP);
    printf("========================================\n");

#ifdef _WIN32
    printf("  Platform: Windows x86_64\n");
    printf("  PID:      %lu\n", GetCurrentProcessId());
#elif defined(__linux__)
    struct utsname un;
    uname(&un);
    printf("  Platform: Linux %s %s\n", un.sysname, un.machine);
    printf("  PID:      %d\n", getpid());
#elif defined(__ANDROID__)
    printf("  Platform: Android ARM64\n");
    printf("  PID:      %d\n", getpid());
#else
    printf("  Platform: Unknown\n");
#endif

    printf("========================================\n");
    printf("  Compiled by ComputeHub Cluster\n");
    printf("========================================\n");
    return 0;
}
