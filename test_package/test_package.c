#include <stdio.h>
#include <string.h>

#define _GNU_SOURCE

#include <ostree-1/ostree.h>



int main(int argc, char *argv[])
{
	ostree_check_version(2020, 06);
	return 0;
}
