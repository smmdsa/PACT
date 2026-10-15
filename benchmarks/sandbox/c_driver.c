/* Compiled only inside Docker as a separate translation unit from candidate source. */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

extern int32_t counter[2];
extern int advance(int32_t index, int32_t amount);
static const int32_t cases[][2] = {@CASES@};
static const int32_t reset_args[2] = @RESET@;

static void state(void) {
    printf("[%" PRId32 ",%" PRId32 "]", counter[0], counter[1]);
}

static int observe(const int32_t args[2]) {
    int status = advance(args[0], args[1]);
    if (status != 0 && status != 1) return 70;
    printf("{\"args\":[%" PRId32 ",%" PRId32 "],\"status\":\"%s\",\"counter\":",
           args[0], args[1], status == 1 ? "ok" : "bounds");
    state(); printf("}");
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) return 71;
    if (strcmp(argv[1], "reset") == 0) return observe(reset_args);
    printf("{\"execution_status\":\"completed\",\"runtime\":{\"engine\":\"gcc\",\"gcc\":\"%s\"},\"initial_counter\":", __VERSION__);
    state(); printf(",\"cases\":[");
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        if (i) printf(",");
        if (observe(cases[i])) return 70;
    }
    printf("],\"reset_case\":"); fflush(stdout);
    pid_t child = fork();
    if (child < 0) return 72;
    if (child == 0) {
        execl(argv[0], argv[0], "reset", (char *)NULL);
        _exit(73);
    }
    int status;
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status) != 0) return 74;
    printf("}\n");
    return 0;
}
