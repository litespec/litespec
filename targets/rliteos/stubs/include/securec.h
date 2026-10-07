/* Minimal stub of Huawei securec (bounds-checking) library headers. */
#ifndef SECUREC_H
#define SECUREC_H
#include <stddef.h>
typedef int errno_t;
#define EOK 0
#define EINVAL 22
#define ERANGE 34
#ifdef __cplusplus
extern "C" {
#endif
errno_t memset_s(void *dest, size_t destMax, int c, size_t count);
errno_t memcpy_s(void *dest, size_t destMax, const void *src, size_t count);
errno_t memmove_s(void *dest, size_t destMax, const void *src, size_t count);
errno_t strcpy_s(char *dest, size_t destMax, const char *src);
errno_t strncpy_s(char *dest, size_t destMax, const char *src, size_t count);
errno_t strcat_s(char *dest, size_t destMax, const char *src);
errno_t sprintf_s(char *dest, size_t destMax, const char *fmt, ...);
errno_t snprintf_s(char *dest, size_t destMax, size_t count, const char *fmt, ...);
errno_t scanf_s(const char *fmt, ...);
errno_t sscanf_s(const char *str, const char *fmt, ...);
#ifdef __cplusplus
}
#endif
#endif
