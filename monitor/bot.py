# -*- coding: utf-8 -*-

from twisted.internet import protocol
from twisted.python import log
from twisted.words.protocols import irc


class MonitorBot(irc.IRCClient):
	def connectionMade(self):
		"""Called when a connection is made."""
		self.nickname = self.factory.nickname
		self.realname = self.factory.realname
		irc.IRCClient.connectionMade(self)
		log.msg("connectionMade")

	def connectionLost(self, reason):
		"""Called when a connection is lost."""
		irc.IRCClient.connectionLost(self, reason)
		log.msg("connectionLost {!r}".format(reason))

	# callbacks for events

	def signedOn(self):
		"""Called when bot has successfully signed on to server."""
		log.msg("Signed on")
		if self.nickname != self.factory.nickname:
			log.msg('Your nickname was already occupied, actual nickname is "{}".'.format(self.nickname))
		self.join(self.factory.channel)

	def joined(self, channel):
		"""Called when the bot joins the channel."""
		log.msg("[{nick} has joined {channel}]".format(nick=self.nickname, channel=self.factory.channel,))

	def privmsg(self, user, channel, msg):
		"""Called when the bot receives a message."""
		sendTo = None
		prefix = ''
		senderNick = user.split('!', 1)[0]
		if channel == self.nickname:
			# Reply back in the query / privmsg
			sendTo = senderNick
		elif msg.startswith(self.nickname):
			# Reply back on the channel
			sendTo = channel
			prefix = senderNick + ': ' #Mark message so people know what is going on
		else:
			msg = msg.lower()
			if msg in ['!hi']:
				sendTo = channel
				prefix = senderNick + ': '
		if sendTo:
			reply = "Hello."
			self.msg(sendTo, prefix + reply)
			log.msg(
				"sent message to {receiver}, triggered by {sender}:\n\t{reply}"
				.format(receiver=sendTo, sender=senderNick, reply=reply)
			)

class MonitorBotFactory(protocol.ClientFactory):
	protocol = MonitorBot

	def __init__(self, channel, nickname, realname):
		"""Initialize the bot factory with our settings."""
		self.channel = channel
		self.nickname = nickname
		self.realname = realname
