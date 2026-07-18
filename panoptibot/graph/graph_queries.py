from __future__ import annotations

from datetime import UTC, datetime, timedelta


def recent_cutoff(hours: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


SUMMARY_CANDIDATES_QUERY = """
MATCH (m:Message)-[:IN_CHANNEL]->(c:Channel)
MATCH (author:User)-[:SENT]->(m)
WHERE coalesce(m.deleted, false) = false AND m.created_at >= $cutoff AND author.id <> $user_id
OPTIONAL MATCH (reply:Message)-[:REPLIED_TO]->(m)
OPTIONAL MATCH (:User)-[reacted:REACTED_TO]->(m)
WHERE reacted.removed_at IS NULL
WITH m, c, author, $user_id AS user_id, count(DISTINCT reacted) AS reaction_count, count(DISTINCT reply) AS reply_count
CALL (author, user_id) {
  OPTIONAL MATCH (viewer:User {id: user_id})-[rel:INTERACTED_WITH]->(author)
  RETURN coalesce(rel.weight, 0) AS interaction_frequency_between_users
}
CALL (author, user_id) {
  OPTIONAL MATCH (viewer:User {id: user_id})-[:SENT]->(reply_message:Message)-[:REPLIED_TO]->(:Message)<-[:SENT]-(author)
  RETURN count(DISTINCT reply_message) AS prior_reply_count_between_users
}
CALL (author, user_id) {
  OPTIONAL MATCH (viewer:User {id: user_id})-[reaction:REACTED_TO]->(:Message)<-[:SENT]-(author)
  WHERE reaction.removed_at IS NULL
  RETURN count(DISTINCT reaction) AS prior_reaction_count_between_users
}
RETURN m.id AS message_id,
       m.created_at AS created_at,
       m.content_length AS message_length,
       m.emoji_count AS emoji_count,
       m.sticker_present AS sticker_present,
       m.attachment_present AS attachment_present,
       reaction_count AS reaction_count,
       reply_count AS reply_count,
       author.id AS author_id,
       c.id AS channel_id,
       coalesce(m.mention_ids, []) AS mention_ids,
       interaction_frequency_between_users AS interaction_frequency_between_users,
       prior_reply_count_between_users AS prior_reply_count_between_users,
       prior_reaction_count_between_users AS prior_reaction_count_between_users
ORDER BY m.created_at DESC
LIMIT $limit
"""


ACTIVITY_STATS_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
RETURN count(m) AS total_messages,
       count(DISTINCT u) AS active_users,
       sum(m.content_length) AS total_content_length
"""


TOP_USERS_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
RETURN u.id AS user_id, count(m) AS message_count
ORDER BY message_count DESC
LIMIT $limit
"""


EMOJI_COUNTS_QUERY = """
MATCH (:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
UNWIND coalesce(m.emoji_list, []) AS emoji
WITH emoji, m.id AS message_id
RETURN emoji, count(DISTINCT message_id) AS usage_count
ORDER BY usage_count DESC
LIMIT $limit
"""


INTERACTION_GRAPH_QUERY = """
MATCH (src:User)-[rel:INTERACTED_WITH]->(dst:User)
WHERE rel.last_seen_at >= $cutoff
RETURN src.id AS source_user, dst.id AS target_user, rel.weight AS weight
ORDER BY weight DESC
LIMIT $limit
"""

REACTION_NETWORK_QUERY = """
MATCH (reactor:User)-[r:REACTED_TO]->(m:Message)<-[:SENT]-(author:User)
WHERE r.removed_at IS NULL AND m.created_at >= $cutoff
RETURN reactor.id AS source_user, author.id AS target_user, count(r) AS weight
ORDER BY weight DESC
LIMIT $limit
"""

REPLY_INFLUENCE_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)<-[:REPLIED_TO]-(reply:Message)
WHERE m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
RETURN u.id AS user_id, count(reply) AS reply_count
ORDER BY reply_count DESC
LIMIT $limit
"""

REACTION_INFLUENCE_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)<-[r:REACTED_TO]-(:User)
WHERE r.removed_at IS NULL AND m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
RETURN u.id AS user_id, count(r) AS reaction_count
ORDER BY reaction_count DESC
LIMIT $limit
"""

BONDS_INTERACTION_QUERY = """
MATCH (src:User)-[rel:INTERACTED_WITH]->(dst:User)
WHERE rel.last_seen_at >= $cutoff
RETURN src.id AS source_user,
       dst.id AS target_user,
       rel.weight AS weight,
       rel.first_seen_at AS first_seen_at
ORDER BY weight DESC
LIMIT $limit
"""

TONE_STATS_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff
  AND coalesce(m.deleted, false) = false
  AND m.caps_ratio IS NOT NULL
RETURN avg(m.caps_ratio) AS avg_caps_ratio,
       avg(m.punctuation_density) AS avg_punctuation_density,
       count(m) AS message_count
"""

ARCHETYPE_DISTRIBUTION_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
RETURN m.archetype AS archetype, count(m) AS count
ORDER BY count DESC
"""

USER_ARCHETYPES_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff
  AND coalesce(m.deleted, false) = false
  AND u.id IN $user_ids
RETURN u.id AS user_id,
       m.archetype AS archetype,
       count(m) AS count
ORDER BY user_id, count DESC
"""

EMOJI_PER_USER_QUERY = """
MATCH (u:User)-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff AND coalesce(m.deleted, false) = false
UNWIND coalesce(m.emoji_list, []) AS emoji
WITH u.id AS user_id, emoji, m.id AS message_id
WITH user_id, emoji, count(DISTINCT message_id) AS usage_count
ORDER BY user_id, usage_count DESC
WITH user_id, collect({emoji: emoji, usage_count: usage_count}) AS emoji_usage
RETURN user_id, emoji_usage[0..$per_user] AS top_emojis
ORDER BY user_id
LIMIT $limit
"""

USER_PROFILE_STATS_QUERY = """
MATCH (u:User {id: $user_id})-[:SENT]->(m:Message)
WHERE m.created_at >= $cutoff AND m.deleted = false
WITH u, COUNT(m) AS total_messages, AVG(m.content_length) AS avg_content_length
OPTIONAL MATCH (u)-[:SENT]->(m2:Message)-[:IN_CHANNEL]->(c:Channel)
WHERE m2.created_at >= $cutoff
WITH u, total_messages, avg_content_length, c.id AS channel_id, COUNT(m2) AS channel_count
ORDER BY channel_count DESC
WITH u, total_messages, avg_content_length, COLLECT({channel_id: channel_id, count: channel_count})[..5] AS top_channels
OPTIONAL MATCH (u)-[:SENT]->(m3:Message)
WHERE m3.created_at >= $cutoff
UNWIND m3.emoji_list AS emoji
WITH u, total_messages, avg_content_length, top_channels, emoji, COUNT(emoji) AS emoji_count
ORDER BY emoji_count DESC
WITH u, total_messages, avg_content_length, top_channels, COLLECT({emoji: emoji, count: emoji_count})[..10] AS top_emojis
OPTIONAL MATCH (u)-[inter:INTERACTED_WITH]->(partner:User)
WITH total_messages, avg_content_length, top_channels, top_emojis, partner.id AS partner_id, inter.weight AS weight
ORDER BY weight DESC
RETURN total_messages, avg_content_length, top_channels, top_emojis, COLLECT({partner_id: partner_id, weight: weight})[..5] AS top_interactions
LIMIT 1
"""
