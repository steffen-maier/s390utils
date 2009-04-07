# /etc/profile.d/s390.csh - set TERM variable

if ( `/sbin/consoletype` == "serial" ) then
    setenv TERM dumb
endif
