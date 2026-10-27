/* shared_impl.cpp — pulls the pure-C protocol codecs in
 * firmware/shared/ into this translation unit. Single point of
 * compilation, no build-config tricks needed. */
extern "C" {
#include "../../shared/can_proto.c"
#include "../../shared/feetech_proto.c"
#include "../../shared/link_proto.c"
}
