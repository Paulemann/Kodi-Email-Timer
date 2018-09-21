#!/usr/bin/python
# -*- coding: utf-8 -*-

# required by jsonrpc_request
import json, urllib2, codecs
from contextlib import closing

# required by checkmail, sendmail
import imaplib, email
from email.utils import parseaddr, formataddr

# required by wake_on_lan:
import socket, struct

# required by sendmail
from email.header import Header

# general
import logging, sys, os, time

# required by read_config
import ConfigParser

# required by utc2loal
from datetime import datetime, tzinfo, timedelta

# required by sendmail
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


# global settings
#_config_file = os.path.splitext(os.path.basename(__file__))[0] + '.ini'
#_log_file_ = os.path.splitext(os.path.basename(__file__))[0] + '.log'
#_debug_ = False

import argparse


def log(message, level='INFO'):
  if _log_file_:
    if level == 'DEBUG' and _debug_:
      logging.debug(message)
    if level == 'INFO':
      logging.info(message)
    if level == 'WARNING':
      logging.warning(message)
    if level == 'ERROR':
      logging.error(message)
    if level == 'CRITICAL':
      logging.crtitcal(message)
  else:
     if level != 'DEBUG' or _debug_:
       print '[' + level + ']: ' + message


def host_is_up(host, port):
  try:
    sock = socket.create_connection((host, port), timeout=3)
  #except socket.timout:
  #  return False
  except:
    return False

  return True


def sendmail(to_address, subject, message):
  #
  # https://code.tutsplus.com/tutorials/sending-emails-in-python-with-smtp--cms-29975
  #

  if not message:
    return False

  html_header='<html>\n<body>\n<pre style="font: monospace">'
  html_footer='</pre>\n</body>\n</html>'

  # create message object instance
  msg = MIMEMultipart('alternative')

  # setup the parameters of the message
  #msg['From'] = _mail_user_
  msg['From'] = formataddr((str(Header('KODI', 'utf-8')), _mail_user_))
  msg['To'] = to_address
  msg['Subject'] = subject

  # add in the message body
  msg.attach(MIMEText(message, 'plain'))
  msg.attach(MIMEText(html_header + message + html_footer, 'html'))

  try:
    #create server
    server = smtplib.SMTP(_smtp_server_)

    server.starttls()

    # Login Credentials for sending the mail
    server.login(_mail_user_, _mail_passwd_)

    # send the message via the server.
    server.sendmail(msg['From'], msg['To'], msg.as_string())

  except:
    log('Unable to send mail.', level='ERROR')
    return False

  finally:
    server.quit()

  return True


def is_mailaddress(a):
  try:
    t = a.split('@')[1].split('.')[1]
  except:
    return False

  return True


def is_hostname(h):
  try:
    t = h.split('.')[2]
  except:
    return False

  return True


def is_int(n):
  try:
    t = int(n)
  except:
    return False

  return True


def read_config():
  global _kodi_, _kodi_mac_, _kodi_port_, _kodi_user_, _kodi_passwd_
  global _imap_server_, _smtp_server_,_mail_user_, _mail_passwd_
  global _search_subject_, _search_channel_, _search_title_, _search_starttime_
  global _reply_subject_, _reply_text_, _allowed_senders_

  if not os.path.exists(_config_file_):
    log('Could not find configuration file \'{}\'.'.format(_config_file_), level='ERROR')
    return False

  log('Reading configuration from file ...')

  try:
    # Read the config file
    config = ConfigParser.ConfigParser()

    config.read([os.path.abspath(_config_file_)])

    _kodi_             = config.get('KODI JSON-RPC', 'hostname')
    _kodi_mac_         = config.get('KODI JSON-RPC', 'macaddress')
    _kodi_port_        = config.get('KODI JSON-RPC', 'port')
    _kodi_user_        = config.get('KODI JSON-RPC', 'username')
    _kodi_passwd_      = config.get('KODI JSON-RPC', 'password')

    if not is_hostname(_kodi_) or not is_int(_kodi_port_):
      log('Wrong or missing value(s) in configuration file (section [KODI JSON-RPC]).')
      return False

    _imap_server_      = config.get('Mail Account', 'imapserver')
    _smtp_server_      = config.get('Mail Account', 'smtpserver')
    _mail_user_        = config.get('Mail Account', 'username')
    _mail_passwd_      = config.get('Mail Account', 'password')

    if not is_hostname(_imap_server_) or not is_hostname(_smtp_server_) or not is_mailaddress(_mail_user_) or not _mail_passwd_:
      log('Wrong or missing value(s) in configuration file (section [Mail Account].')
      return False

    _search_subject_   = config.get('Search Patterns', 'subject').strip(' "\'')
    _search_channel_   = [p.strip(' "\'') for p in config.get('Search Patterns', 'channel').split(',')]
    _search_title_     = [p.strip(' "\'') for p in config.get('Search Patterns', 'title').split(',')]
    _search_starttime_ = [p.strip(' "\'') for p in config.get('Search Patterns', 'starttime').split(',')]

    if not _search_subject_ or not _search_channel_ or not _search_title_ or not _search_starttime_:
      log('Wrong or missing value(s) in configuration file (section [Search Patterns]).')
      return False

    _allowed_senders_  = [p.strip(' "\'') for p in config.get('Allowed Senders', 'mailaddress').split(',')]

    for sender in  _allowed_senders_:
      if not is_mailaddress(sender):
        log(' Wrong or missing value(s) in configuration file (section [Allowed Senders]).')
        return False

    _reply_subject_    = config.get('Reply Message', 'subject')
    _reply_text_       = config.get('Reply Message', 'text')

  except:
    log('Could not process configuration file.', level='ERROR')
    return False

  log('Configuration OK.')

  return True


class Zone(tzinfo):
  def __init__(self,offset,isdst,name):
    self.offset = offset
    self.isdst = isdst
    self.name = name
  def utcoffset(self, dt):
    return timedelta(hours=self.offset) + self.dst(dt)
  def dst(self, dt):
    return timedelta(hours=1) if self.isdst else timedelta(0)
  def tzname(self,dt):
    return self.name


__GMT__  = Zone(0,False,'GMT')
__CEST__ = Zone(1,True, 'CEST')


def utc2local(utctime):
  t = datetime.strptime(utctime,'%Y-%m-%d %H:%M:%S')
  t = t.replace(tzinfo=__GMT__)
  localtime = t.astimezone(__CEST__)

  return localtime


def convert(date):
  try:
    dt = datetime.strptime(date, "%d.%m.%Y %H:%M")
    conv_date = datetime.strftime(dt, "%Y-%m-%d %H:%M")
  except:
    try:
      dt = datetime.strptime(date, "%d.%m.%Y")
      conv_date = datetime.strftime(dt, "%Y-%m-%d")
    except:
      conv_date = date

  return conv_date


def reconvert(date):
  try:
    dt = datetime.strptime(date, "%Y-%m-%d %H:%M")
    conv_date = datetime.strftime(dt, "%d.%m.%Y %H:%M")
  except:
    conv_date = date

  return conv_date


def mixed_decoder(unicode_error):
  err_str = unicode_error[1]
  err_len = unicode_error.end - unicode_error.start
  next_position = unicode_error.start + err_len
  replacement = err_str[unicode_error.start:unicode_error.end].decode('cp1252')

  return u'%s' % replacement, next_position


codecs.register_error('mixed', mixed_decoder)


def jsonrpc_request(method, params=None, host='localhost', port=8080, username=None, password=None):
  url = 'http://{}:{}/jsonrpc'.format(host, port)
  header = {'Content-Type': 'application/json'}

  jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

  if params:
    jsondata['params'] = params

  if username and password:
    base64str = base64.encodestring('{}:{}'.format(username, password))[:-1]
    header['Authorization'] = 'Basic {}'.format(base64str)

  try:
    request = urllib2.Request(url, json.dumps(jsondata), header)
    with closing(urllib2.urlopen(request)) as response:
      data = json.loads(response.read().decode('utf8', 'mixed'))
      if data['id'] == method and data.has_key('result'):
        return data['result']
  except:
    pass

  return None


def channelid(name):
  if not name:
    return 0

  data = jsonrpc_request('PVR.GetChannels',params={"channelgroupid":1}, host=_kodi_, port=_kodi_port_, username=_kodi_user_, password=_kodi_passwd_)
  if data:
    for channel in data['channels']:
      if channel['label'].lower() == name.lower():
        return channel['channelid']

  return 0


def channelname(id):
  if id <= 0:
    return ''

  data = jsonrpc_request('PVR.GetChannels',params={"channelgroupid":1}, host=_kodi_, port=_kodi_port_, username=_kodi_user_, password=_kodi_passwd_)
  if data:
    for channel in data['channels']:
      if channel['channelid'] == id:
        return channel['label'].encode('utf-8')

  return ''


def broadcastid(channelid, title):
  id = []

  if channelid <= 0 or not title:
    return id

  data = jsonrpc_request('PVR.GetBroadcasts',params={'channelid':channelid}, host=_kodi_, port=_kodi_port_, username=_kodi_user_, password=_kodi_passwd_)
  if data:
    for broadcast in data['broadcasts']:
      if title in broadcast['label']:
        id.append(broadcast['broadcastid'])

  return id


def broadcastdetails(broadcastid):
  if broadcastid <= 0:
    return None

  data = jsonrpc_request('PVR.GetBroadcastDetails',params={"broadcastid":broadcastid,"properties":["title","starttime","endtime"]}, host=_kodi_, port=_kodi_port_, username=_kodi_user_, password=_kodi_passwd_)
  if data:
    return data['broadcastdetails']['title'], data['broadcastdetails']['starttime']

  return None


def timers():
  result = []
  data = jsonrpc_request('PVR.GetTimers', params={'properties': ['title', 'starttime', 'channelid']}, host=_kodi_, port=_kodi_port_, username=_kodi_user_, password=_kodi_passwd_)

  if data:
    for timer in data['timers']:

      if str(timer['starttime'])[:19] == '1970-01-01 00:00:00':  # inactive timer
        continue

      result.append((channelname(timer['channelid']), timer['title'].encode('utf-8'), timer['starttime'] ))

  return result


def wake_on_lan(address):
  #
  # Based on script developed by Georg Kainzbauer <http://www.gtkdb.de>
  #

  # extract mac address from argument
  if len(address) == 12:
    mac = address
  elif len(address) == 17:
    mac = address.replace(address[2], '')
  else:
    # invalid length of MAC address
    return False

  # create magic packet
  magic_packet = ''.join(['FF' * 6, mac * 16])
  send_data = ''
  for i in range(0, len(magic_packet), 2):
    send_data = ''.join([send_data, struct.pack('B', int(magic_packet[i: i + 2], 16))])

  # send magic packet
  dgramSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  dgramSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  dgramSocket.sendto(send_data, ("255.255.255.255", 9))

  return True


def checkmail():
  result = []

  mail = imaplib.IMAP4_SSL(_imap_server_)

  try:
    mail.login(_mail_user_, _mail_passwd_)
    mail.select('INBOX')

    log('Checking mail server ...')

    #today = datetime.date.today().strftime("%d-%b-%Y")
    #result, data = mail.uid('search', None, 'UNSEEN', 'SUBJECT', _search_subject_, 'ON', today)

    status, data = mail.uid('search', None, 'UNSEEN', 'SUBJECT', _search_subject_)

    if status == 'OK':
      if data[0]:
        log('Found {} new mail(s) with matching subject \'{} \'.'.format(len(id_list), _search_subject_))

        uid_list = data[0].split()
        for uid in uid_list:
          channel = ''
          title = ''
          starttime = ''

          status, data = mail.uid('fetch', uid, '(RFC822)')

          raw_email = data[0][1]
          message = email.message_from_string(raw_email)

          sender = parseaddr(message['From'])
          if sender not in _allowed_senders_:
            log('{} is not in the allowed sender list.'.format(sender))
            continue

          for part in message.walk():
            if part.get_content_type() == 'text/plain':

              plain_text = part.get_payload()
              lines = plain_text.splitlines()

              for line in lines:
                if len(line.split(':', 1)) > 1:

                  if line.split(':', 1)[0].strip() in _search_channel_:
                    channel = line.split(':', 1)[1].strip()

                  if line.split(':', 1)[0].strip() in _search_title_:
                    title = line.split(':', 1)[1].strip()

                  if line.split(':', 1)[0].strip() in _search_starttime_:
                    starttime = line.split(':', 1)[1].strip()

          if (channel and title) or (not channel and not title and not starttime):
            result.append((sender, channel, title, convert(starttime)))

          #mail.uid('store', uid, '+FLAGS', '(\\Seen)')
          mail.uid('store', uid, '+FLAGS', '(\\Deleted)')
          mail.expunge()

      else:
        log('No new mail')

  finally:
    try:
      mail.close()
    except:
      pass
    mail.logout()

  return result


if __name__ == '__main__':
  global _config_file_, _log_file_, _debug_

  parser = argparse.ArgumentParser(description='Python script to add kodi pvr timers based on email content')

  parser.add_argument('-d', '--debug', dest='debug', action='store_true', help="Output debug messages (Default: False)")
  parser.add_argument('-l', '--logfile', dest='log_file', default=None, help="Path to log file (Default: None=stdout)")
  parser.add_argument('-c', '--config', dest='config_file', default=os.path.splitext(os.path.basename(__file__))[0] + '.ini', help="Path to config file (Default: <Script Name>.ini)")

  args = parser.parse_args()

  _config_file_ = args.config_file
  _log_file_ = args.log_file
  _debug_ = args.debug

  if _log_file_:
    logging.basicConfig(filename=_log_file_, format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG)

  log('Output Debug: {}'.format(_debug_), level='DEBUG')
  log('Log file:     {}'.format(_log_file_), level='DEBUG')
  log('Config file:  {}'.format(_config_file_), level='DEBUG')

  if not read_config():
     sys.exit()

  new_timer = False

  timer_schedule = checkmail()

  if timer_schedule and not host_is_up(_kodi_, _kodi_port_):
    log('Trying to wake up kodi ...')

    if wake_on_lan(_kodi_mac_):
      time.sleep(30)

  for sender, channel, title, starttime in timer_schedule:
    if channel:
      channel_id = channelid(channel)

      if channel_id > 0:
        log('Found channel id {} for channel name \'{}\''.format(channel_id, channel))

        bcst_id_list = broadcastid(channel_id, title)
        if list:
          log('{} match(es) for title \'{}\' found in broadcast list for channel \'{}\''.format(len(bcst_id_list), title, channel))

          if not starttime:
            log('No start time given. Will create timer for each matching title in broadcast list.')

          for broadcast_id in bcst_id_list:
            broadcast, start = broadcastdetails(broadcast_id)
            log('Found broadcast id {} for broadcast \'{}\' on channel \'{}\'.'.format(broadcast_id, broadcast, channel), level='DEBUG')

            if starttime and starttime not in str(utc2local(start)):
              log('Given start time {} does not match start time {} of broaadcast \'{}\''.format(starttime, start, broadcast), level='DEBUG')
              continue

            if not starttime:
              pass

            new_timer = True

            log('Adding new timer for broadcast \'{}\' on channel \'{}\' at start time {} ...'.format(broadcast, channel, str(utc2local(start))))
            response = jsonrpc_request('PVR.AddTimer',params={"broadcastid":broadcast_id}, host=_kodi_, username=_kodi_user_, password=_kodi_passwd_)
            if response:
              log('Received response from KODI. Seems that timer has been added.')
            else:
              log('Couldn\'t read response from KODI. Seems that timer has not been added.', level='ERROR')

            if starttime and starttime in str(utc2local(start)):
              break
        else:
          log('Could not find broadcast id for title \'{}\' on channel \'{}\'.'.format(title, channel), level='ERROR')

      else:
        log('Could not find channel id for channel \'{}\'.'.format(channel), level='ERROR')

  sender_list = set()
  for sender, channel, title, starttime in timer_schedule:
    sender_list.add(sender)

  if sender_list and _reply_subject_ and _reply_text_:
    if new_timer:
      log('Waiting for KODI to add timer(s) ...')
      time.sleep(30)  # allow 30 secs for KODI to add timers

    log('Retrieving current timer list from KODI ...')
    timer_list = timers()

    message = _reply_text_
    message += '\n\n{:<18} {:<34} {}'.format(_search_starttime_[0] + ':', _search_channel_[0] + ':', _search_title_[0] + ':')
    if len(timer_list) == 0:
      log('>>> Timer list is empty. <<<')
    else:
      for t_channel, t_title, t_starttime in timer_list:
        message += '\n{:<18} {:<34} {}'.format(reconvert(str(utc2local(t_starttime))[:16]), t_channel, t_title)

    for sender in sender_list:
      log('Sending timer list to {} ...'.format(sender))
      sendmail(sender, _reply_subject_, message)
